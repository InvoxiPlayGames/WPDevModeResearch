#!/usr/bin/python3

# Attempts, and likely fails, dev mode registration on a connected Windows Phone
# script by Emma/InvoxiPlayGames, 2024

import sys
import struct
import socket

# Message header:
# byte 0x10
# byte commandType
# ushort packetLength
# commandType values:
#   0x01 - GetStatus
#   0x02 - Lock
#   0x03 - Unlock
#   0x04 - SwitchToInt
#   0x51 - ResultResponse
#   0x52 - ErrorResponse

def build_get_status_request():
    return bytes([0x10, 1, 0, 0])

def build_lock_request(cookie: str):
    cookie_bytes = cookie.encode(encoding="utf-8")
    auth_token = struct.pack("<bh", 1, len(cookie_bytes)) + cookie_bytes
    header = struct.pack("<bbh", 0x10, 2, len(auth_token))
    return header + auth_token

def build_unlock_request(cookie: str, isInt = False):
    cookie_bytes = cookie.encode(encoding="utf-8")
    auth_token = struct.pack("<bh", 1, len(cookie_bytes)) + cookie_bytes
    use_prod = 1
    if isInt:
        use_prod = 0
    int_state = struct.pack("<bhh", 2, 2, use_prod)
    header = struct.pack("<bbh", 0x10, 3, len(auth_token) + len(int_state))
    return header + auth_token + int_state

def build_switch_to_int_request():
    return bytes([0x10, 4, 0, 0])

def parse_response(response_bytes: bytes):
    (header, msg_type, length, always1, code_len, code) = struct.unpack("<bbhbhI", response_bytes)
    return (msg_type == 0x51, code)

def print_usage():
    print("usage: ./attempt_dev_mode_registration.py [port] [verb] [optional: cookie]")
    print("port: 27177 for WP8, 27077 for WP7")
    print("verbs: status, lock, unlock, switchint")

def get_error_string(code):
    return {
        0xC: "device is locked, please unlock the screen",
        0xD: "device is locked on the internal environment",
        0xE: "device is already registered to the internal environment",
        0xF: "device already has a non-internal account registered",
        0x10: "device provisioning on internal environment failed",
        0x11: "device failed to initialise Windows Live on the internal environment",
        0x12: "device has dev unlocking disabled",
        0x64: "device could not connect to developer services",
        0x80004001: "command not implemented on the device (0x80004001)"
    }.get(code, "unknown " + hex(code))    

def do_status(s: socket.socket):
    s.send(build_get_status_request())
    resp_bytes = s.recv(11)
    (success, code) = parse_response(resp_bytes)
    if success:
        if code == 2:
            print("device status: registered")
        elif code == 1:
            print("device status: unregistered")
        else:
            print("device status: unknown")
    else:
        print("error: " + get_error_string(code))
    return

def do_unlock(s: socket.socket, cookie: str):
    s.send(build_unlock_request(cookie, False))
    resp_bytes = s.recv(11)
    (success, code) = parse_response(resp_bytes)
    if success:
        print("successfully enabled developer mode! result code " + hex(code))
    else:
        print("error: " + get_error_string(code))
    return

def do_lock(s: socket.socket, cookie: str):
    s.send(build_lock_request(cookie))
    resp_bytes = s.recv(11)
    (success, code) = parse_response(resp_bytes)
    if success:
        print("successfully disabled developer mode! result code " + hex(code))
    else:
        print("error: " + get_error_string(code))
    return

def do_switchint(s: socket.socket):
    s.send(build_switch_to_int_request())
    resp_bytes = s.recv(11)
    (success, code) = parse_response(resp_bytes)
    if success:
        print("successfully switched to internal environment! result code " + hex(code))
    else:
        print("error: " + get_error_string(code))

def main(argc, argv):
    if argc < 2:
        print_usage()
        return
    
    port = int(argv[0])
    verb = argv[1]
    valid_verbs = ["status", "lock", "unlock", "switchint"]
    if verb not in valid_verbs:
        print_usage()
        return
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(("127.0.0.1", port))
    except ConnectionRefusedError:
        print("failed to connect to port")
        if port == 27077:
            print("make sure the Zune application is open, and wait a few moments")
        elif port == 27177:
            print("make sure IPtoUSBSvc is running")
        else:
            print("try either 27177 (WP8) or 27077 (WP7)")
        return
    except:
        print("unknown error occurred while connecting")
        return
    
    cookie = "Cookie: SWMAuth=EmmaWasHere"
    if argc >= 3:
        cookie = argv[2]
    
    if verb == "status":
        do_status(s)
    elif verb == "lock":
        do_lock(s, cookie)
    elif verb == "unlock":
        do_unlock(s, cookie)
    elif verb == "switchint":
        do_switchint(s)
    
    s.close()
    return

if __name__ == "__main__":
    argc = len(sys.argv[1:])
    argv = sys.argv[1:]
    main(argc, argv)
