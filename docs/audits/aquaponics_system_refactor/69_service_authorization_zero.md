# Service authorization inventory

Application API and service authorization now derives access from database-backed role permissions and resource ownership. No direct `User.system_role` authorization comparison remains in those layers. System role remains an identity/session attribute and is used for seed and membership eligibility only.
