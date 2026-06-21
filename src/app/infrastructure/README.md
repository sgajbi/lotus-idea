# Infrastructure Layer

Concrete adapters belong here and should implement interfaces from `app.ports`. Infrastructure code
may depend on HTTP clients, databases, queues, or files, but domain and application code must not.
