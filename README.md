SlimSMTP
========

A Simple and Slim SMTP server aiming for a minimalistic and simple design.

Requirements
============

 * Python3.9+
 * python-dnspython
 * python-systemd *(Optional)*

Installation
============

```
$ git clone https://github.com/Torxed/slimSMTP
$ cd slimSMTP
$ python example.py
```

Configuration
=============

In `example.py` there is a configuration structure.<br>
You'll need basic understanding of Python to navigate this.

The configuration looks like this:
```python
slimSMTP.Configuration(
    port=25,
    address='',
    realms=[
        slimSMTP.Realm(name='hvornum.se')
    ]
)
```

Where `port` is the port the server will listen on.<br>
`address` is the IP address of the interface you wish to bind to, `''` means any interface.<br>
`realms` is a list of domains that the server should accept mail to.

Meaning when someone sends a mail to `github.test+label@hvornum.se`, we will only accept it<br>
if we have a realm configured for `name='hvornum.se'`.