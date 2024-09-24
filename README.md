# Windows Phone Dev Mode Research

This is just a repo to put my notes on how Windows Phone 7 and 8 handle
activating "developer mode", enabling XAP/APPX/APPXBUNDLE sideloading.

Microsoft started killing off these features after 2017, when WP8.1 was
discontinued, and as of 2020 you could not enable developer mode nor download
apps from the Windows Store, rendering many Windows Phones as effectively
glorified dumb phones without a jailbreak.

Using [WPInternals](https://github.com/ReneLergner/WPinternals) it is
possible to "jailbreak" Windows Phone 8.1 devices to enable sideloading /
dev mode functionality and a lot more, but this only works well on Lumia devices
due to relying on a bootloader vulnerability, and can't be used on the very
different Windows CE-based Windows Phone 7. **If you are on a Nokia/Microsoft
Lumia Windows Phone 8.1 device, you can use WPInternals to jailbreak!**

This documentation isn't useful by itself, it's to be used as a springboard for
future research or vulnerability probing.

# Activation Process

This research comes mostly from Windows Phone 8.1. Differences in
Windows Phone 7 will be provided where available and necessary.

## PC Side

The "Windows Phone Developer Registration" application (PhoneReg.exe), provided
by the SDK, opens a web view control to go through the OAuth2 client flow for
the client ID `00000000480CB72D` to get a valid service ticket. It then makes
the following request to the device unlock service:

```
POST https://deviceunlockservice.windowsphone.com/passport/login.aspx?url=%2f&wa=wsignin1.0 HTTP/1.1
Content-Type: application/x-www-form-urlencoded
Host: deviceunlockservice.windowsphone.com
Content-Length: 1116
Expect: 100-continue
Connection: Keep-Alive

t=[snip]
```

The servers are down, however the code does not care about the response headers
or body, aside from the HTTP response code, which must be 200 OK. A response
that will be seen as successful is as follows:

```
HTTP/1.1 200 OK
Content-Length: 2
Content-Type: text/plain; charset=utf-8
Set-Cookie: SWMAuth=NotARealAuthToken;

Hi
```

The `SWMAuth` cookie result from this is then sent to the device over IP-to-USB
service port `27177` (**Windows Phone 7**: `27077`) via TCP. The script inside
[attempt_dev_mode_registration.py](/scripts/attempt_dev_mode_registration.py)
will build the requests and parse the responses sent by the device. **Do not run
this tool if you have dev mode activated, it will disable sideloading apps!**

**Windows Phone 7:** A login attempt is made using msidcrl40.dll directly to
`https://login.live.com/RST2.srf`, using credentials given in text fields in
the application itself (requires App Passwords in 2024). It then logs into
`https://api.marketplace.windowsmobile.com/passport/login.aspx?ppud=4&wa=wsignin1.`
to get the `SWMAuth` cookie.

## Windows Phone Side

This is all handled by `\PROGRAMS\DEVICEREG\DeviceReg.exe` in the MainOS
partition.

Upon receiving the unlock command, if the device is unlocked and doesn't have
dev mode already activated, or disabled via MDM/carrier policy, the phone itself
will make the request to the Windows Phone developer services endpoint, which is
specified in the registry as `PortalUrlProd` in
`HKLM\Software\Microsoft\DeviceReg`. (`PortalUrlInt` if `isInt` is set in the
packet sent from the PC.)

```
GET https://developerservices.windowsphone.com/Services/WindowsPhoneRegistration.svc/01/2010/RegisterDevice?deviceId=[snip]&fullDeviceId=[snip]&friendlyName=Windows%20Phone HTTP/1.1
Cache-Control: no-cache
Connection: Keep-Alive
Pragma: no-cache
Cookie: SWMAuth=NotARealAuthToken
Host: developerservices.windowsphone.com
```

where `deviceId` is a GUID representation of a device ID, and `fullDeviceId` is
a URL encoded binary blob of the device ID. The original services are down, but
an expected response should look similar to: (courtesy of ChevronWP7)

```
HTTP/1.1 200 OK
Content-Length: 523
Content-Type: text/xml; charset=utf-8

<?xml version="1.0" encoding="utf-8"?>
<ResponseOfRegisteredDeviceStatus xmlns="Microsoft.WindowsMobile.Service.Marketplace" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
    <ResponseCode>0x00000000</ResponseCode>
    <ResponseMessage i:nil="true">
        <Entity xmlns:a="http://schemas.datacontract.org/2004/07/Microsoft.WindowsMobile.Service.Marketplace.BLLDevPortal.Entities">
            <a:DaysLeft>365</a:DaysLeft>
            <a:AppsAllowed>10</a:AppsAllowed>
        </Entity>
    </ResponseMessage>
</ResponseOfRegisteredDeviceStatus>
```

On Windows Phone 8.1 (8.10.15148.160), the server certificate is not validated
upon connection, but after the response has been received. The certificate chain
is validated by the `AuthRoot` in the HKEY_LOCAL_MACHINE registry, and is
verified to have the server's Common Name match the one used to initiate the
request.

**Windows Phone 7**: Cert pinning behaviour differs based on versions - early
enough versions do not use proper cert pinning and as such developer mode can
be enabled. This was used by the ChevronWP jailbreak. Later versions check the
SSL certificate after receiving the response, but they check for a specific cert
fingerprint and CA name (`Microsoft Internet Authority`)
