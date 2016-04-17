SlimSMTP
========

A Simple and Slim SMTP server aiming for a minimalistic and simple design.


Key features
============
* 1 executable (Minimal software requirements)
* Simple to configure (top part of the executable)
* Less code `(~500 rows)` for a more secure overview
* Easy to administrate and set up

Notes about the binary blob and helpers.source:
======

Just to get a better overview of the main code blocks..<br>
I did what you normally shouldn't do and that is compress<br>
the raw code into a gzip blob which I in runtime deflate and compile.<br>

Now before you say no, this highly temporary and sort of an experiment.<br>
Once I've restructured the main code blocks this code will be brough back in regular form.

Installation
============

If you're planning on using PostgreSQL as a backend for the `storage` mapper, this is your bare essentials:

    CREATE TABLE IF NOT EXISTS smtp (id bigserial PRIMARY KEY, mailbox varchar(255), domain varchar(255), account_backend varchar(20), UNIQUE (mailbox, domain));
    INSERT INTO smtp (mailbox, domain, account_backend) VALUES('anton', 'example.com', 'PAM');
    INSERT INTO smtp (mailbox, domain, account_backend) VALUES('anton', '@SOCIAL', 'ALIAS');
    INSERT INTO smtp (mailbox, domain, account_backend) VALUES('facebook', 'example.com', '@SOCIAL');
    INSERT INTO smtp (mailbox, domain, account_backend) VALUES('twitter', 'example.com', '@SOCIAL');

 * account_backend == PAM - Means that this storage should be mapped against the Unix local homedirectory.
 * account_backend == @SOCIAL - Means this account is a shared mailbox and is a soft-map for it.
 * domain == @SOCIAL - Means it's a soft-domain pointing at a shared mailbox called "SOCIAL".

Configuration
=============

The basic idea is that you simply modify the top part of the code, the dictionary itself.<br>
This consist of a few settings which I'll try to explain here:

 * core._socket    - Contains the address and ports to listen on incomming SMTP connections (default is 25 for ext->int deliveries)
 * core.SSL        - Contains certificate and version information and a flag to enforce SSL for _all_ sockets.
 * core.domain     - A basic way to configure what domain to host (when external emails arrive in to the server)
 * core.supports   - A simple string of the options we support, important here are DOMAIN, STARTTLS and AUTH PLAIN.
 * core.users      - Now, this is **NOT** email address, it's the accounts we can auuthenticate for int->ext mail deliveries.
                     We also got aliases here such as a `@PAM` which will force the AUTH block to check against PAM.
                     `@POSTGRESQL` is not yet implemented as a user auth backend (if needed, I'll add it. Perhaps for Windows users?)
 * core.relay      - If we're behind a router/firewall that blocks outbound SMTP but has a relay-server somewhere, use this setting.
 * core.external   - This is used to say if we'll allow plain-text emails to pass from us to say google, hotmail or tutanoa for instance.
 * core.storages   - Consists of 4 things, soft-links (aliases) such as `@PAM` and `@POSTGRESQL`. These two will go out to the external
                     source, for instance postgresql and check in the database weither a email/mailbox is defined and if so where to deliver
                     the recieved email. `@PAM` would check with PAM if the user exists and then deliver to that users home directory.
                     Then there's `default` which is a default container for any email that is not defined, sorta like a garbage collector.
                     The last option is to put email addresses and their storage location in the dictionary,
                     for instance `'anton@domain.com' : '/home/anton/Maildir/'` would create `anton@domain.com` and deliver emails to the supplied path.
 * core.postgresql - Credentials for the database backend (if opted in for it)

How to run
==========

It shouldn't be more to it than to run:

    # python slim_smtp.py

If any error messages pop up it's probably a missing folder structure in `core['storages']`.<br>
Check your folder structures or database credentials (if you opt in to use PostgreSQL).

Todos
=====

There's a bunch of stuff to finish before this can be released as a major version,<br>
But for now this is a stable beta release ready for testing.

Here's a few things that's ontop of the list before a release is made:

 * [Security sanity check on the code](https://github.com/Torxed/SlimSMTP/issues/3)
 * ```Error handling```
 * ```Restructure the code to be more logical```
 * [Test and verification by a non-developer](https://github.com/Torxed/SlimSMTP/issues/5)
