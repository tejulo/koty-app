# DEV-9: Configurar el entorno local con PostgreSQL

## Problema

El equipo necesita levantar las dependencias locales de forma repetible sin configurar servicios manualmente. Actualmente no existe Docker Compose ni configuración de base de datos PostgreSQL local, lo que impide iniciar los componentes del monorepo que dependen de persistencia.

## Objetivo

Establecer un procedimiento automatizado para iniciar, detener y validar una instancia PostgreSQL local mediante Docker, con plantillas de variables de entorno seguras y documentación del setup.

## Alcance

1. **Docker Compose para PostgreSQL**: Servicio PostgreSQL configurable desde el repositorio, iniciable y detenible con comandos documentados.
2. **Validación de variables de entorno**: Cada proceso (API, Worker) valida sus variables obligatorias al arrancar y falla con mensaje claro si falta alguna.
3. **Plantilla de variables de entorno**: Archivo `.env.example` con todas las variables previstas, sin secretos reales.
4. **Variables de navegador seguras**: El frontend no expone credenciales ni secretos en variables públicas.
5. **Documentación del procedimiento de setup**: Sección en `CONTRIBUTING.md` o `README.md` que permita dejar un entorno limpio operativo.

## Fuera de Alcance

- Implementación de autenticación o autorización.
- Migraciones de base de datos.
- Integración con servicios externos (email, SMS, etc.).
- Pipeline CI/CD o despliegue en producción.
- Configuración de Prisma o cualquier ORM.

## Impacto Esperado

- Un desarrollador puede levantar PostgreSQL local con un solo comando documentado.
- Los procesos fallan de forma clara e informativa si falta una variable de entorno obligatoria.
- Los secretos no se exponen en el repositorio ni en el frontend.
- El entorno local es reproducible y documentado.
