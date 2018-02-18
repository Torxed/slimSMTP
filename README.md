SlimSMTP
========

A Simple and Slim SMTP server aiming for a minimalistic and simple design.

Key features
============
* Simple to configure via configuration.py
* Less code `(~500 rows)` for a more secure overview
* Easy to administrate and set up

Plugins:
======
The main code can be run as is,<br>
it will default to some primitive mail storage solutions (PAM, configured users and Maildir syntax).

The plugins are optional, but they can expand slim_smtp's functionality without complicating the main functionality.<br>

TODO: Bring back the plugin support.

Installation
============

`git clone` this repo, or if you're on Arch Linux:

    # pacaur -S slimSMTP

Configuration
=============

The basic idea is that you simply modify `configuration.py` in the code the dictionary itself or under `/etc/slimSMTP/`.<br>
This consist of a few settings which I'll try to explain here:

 * pidfile         - It is what it is, it's the pid file
 * ssl             - Contains certificate and version information and a flag to enforce SSL for _all_ sockets and mail-deliveries.
 * domains         - A sub-dictionary to enable support for multiple domain configurations.
 * users           - Now, this is **NOT** email address, it's the accounts we can authenticate for external mail deliveries.
                     The fields which needs to be defined for each user are `password` which, will be required if the sender tries to send external emails.
                     `storage` which is the storage class slimSMTP will use to call `.store(from, to, message)` on in order to store the incomming email.
 * core.relay      - TODO: Bring back relay possibilities. Didn't prioritize it in `v0.1.0` code rewrite.
 * mailboxes       - For now, these are key, value pairs where the key is the full email address and the value is the username it belongs to.
 * postgresql      - Credentials for the database backend (if opted in for it) [TODO: bring back PostgreSQL mailbox delivery options]

How to run
==========

It shouldn't be more to it than to run:

    # python slim_smtp.py

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
