SlimSMTP
========

A Simple and Slim SMTP server aiming for a minimalistic and simple design.

Requirements
============

 * Python3.5+
 * python-pam
 * python-psycopg2
 * python-systemd

Installation
============

`git clone` this repo, or if you're on Arch Linux:

    # pacaur -S slimSMTP

Configuration
=============

The basic idea is that you simply modify `configuration.py` in the code the dictionary itself or under `/etc/slimSMTP/`.<br>
This consist of a few settings which I'll try to explain here:

 * domains         - A sub-dictionary to enable support for multiple domain configurations.
 * users           - Now, this is **NOT** email address, it's the accounts we can authenticate for external mail deliveries.
                     The fields which needs to be defined for each user are `password` which, will be required if the sender tries to send external emails.
                     `storage` which is the storage class slimSMTP will use to call `.store(from, to, message)` on in order to store the incomming email.
 * mailboxes       - For now, these are key, value pairs where the key is the full email address and the value is the username it belongs to.
 * filepermissions - Unless `owner=...` is specified in the `users` configuration, these filepermissions will be used. (note: `user` definitions override `filepermissions`!)
 * ssl             - Contains certificate and version information and a flag to enforce SSL for _all_ sockets and mail-deliveries.
 * relay           - TODO: Bring back relay possibilities. Didn't prioritize it in `v0.1.0` code rewrite.
 * postgresql      - Credentials for the database backend (if opted in for it) [TODO: bring back PostgreSQL mailbox delivery options]
 * pidfile         - It is what it is, it's the pid file

How to run
==========

It shouldn't be more to it than to run:

    # python slim_smtp.py

Changelog
=========

### 0.1.2
 * Support for `/etc/slimSMTP/configuration.py` configuration location.
 * Support looking for helper, storage and other libraries under `/usr/lib/slimSMTP/*.py`
 * Optimized some of the log events
 * Added file permissions for all incomming emails based on configration (`owner` in `user` definitions or `filepermissions`)
 * Added some additional error handling (still far from done)
 * Added `custom_load()` that will import a library/module based on a full path rather than traditional `import x` (**Python3.5+**)

### 0.1.1
 * Default (unknown recipients) mailbox storage per domain via `*@domain.com` definition.

### 0.1.0
 * Rewrite, supports basic recieving, auth and sending internal emails.

Todos
=====

There's a bunch of stuff to finish before this can be released as a major version,<br>
But for now this is a stable beta release ready for testing.

Here's a few things that's ontop of the list before a release is made:

 * More client error message handling. There's a lot of SMTP stuff missing.
 * Fix a lot of config key assumptions and in general dictionary assumptions.
 * [Security sanity check on the code](https://github.com/Torxed/SlimSMTP/issues/3)
 * ```Error handling```
 * ```Restructure the code to be more logical``` (might have done this now v0.1.0)
 * [Test and verification by a non-developer](https://github.com/Torxed/SlimSMTP/issues/5)
