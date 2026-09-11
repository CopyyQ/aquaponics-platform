# Scope and ownership validation

Canonical nested resources always constrain the child identifier by its parent system/device identifier. A resource from another system returns 404 after the scope check, preventing IDOR. Management additionally requires system ownership or an OWNER/TECHNICIAN membership, unless the caller has an explicit global management permission.
