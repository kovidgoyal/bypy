bypy can auto-build Linux VMs. In the project folder, just run::

    python ../bypy linux 64 vm
    python ../bypy linux arm64 vm

To build the VMs based on the base image specified in the projects
:file:`bypy/linux.conf` file.

.. note::
   Access to these machines is via SSH via publickey authentication.
   For that to work, the creation script automatically injects your
   :file:`~/.ssh/authorized_keys` into the created VM. Make sure you have
   automatic password-less publickey authentication working for at least
   one key in :file:`~/.ssh/authorized_keys`.
