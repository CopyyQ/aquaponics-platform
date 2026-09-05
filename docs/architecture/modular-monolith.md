# Modular monolith

Aquaponics Platform ships as one application with multiple runtimes: FastAPI API, MQTT consumer, scheduler, React frontend, Mosquitto and PostgreSQL. They share a repository, database, models, application services, authorization policy and release lifecycle.

Modules are Identity, Projects, Devices, Catalogs, Sensing, Telemetry, Alerts and Actuation. HTTP/MQTT/jobs are adapters; use cases and transaction boundaries live in application services. The database is shared, but table ownership and Project-scoped access remain explicit.

Microservices are not justified because modules require atomic Device-template instantiation, shared tenant authorization and coordinated migrations, while operational scale has not shown independent deployment needs. Consider extraction only after measured scaling/ownership requirements, stable public contracts and an approved data-consistency plan.

Add a module by defining owned tables/use cases/public service interface, keeping transport adapters thin, documenting allowed reads/calls, and adding architecture/authorization tests.
