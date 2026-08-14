# Diseno de tickets para el Incremento 0

## Alcance

- Fuente: `CONTEXT.md`.
- Incremento: `0. Plataforma segura`.
- Destino: workspace `tejulo`, team `dev`, proyecto `koty-app`.
- Tamano objetivo: uno a tres dias por ticket.
- Estrategia: capacidades verticales ordenadas por dependencias.
- Pruebas: forman parte del ticket que introduce la capacidad; no se duplican en tickets QA paralelos.
- Limite: el logo privado, `OwnerPortalGrant` y las configuraciones de dominios posteriores se implementan en los incrementos que introducen archivos, cartera y finanzas.

## Tickets

### 1

Título: Inicializar el monorepo de la plataforma

Descripción: Como equipo de desarrollo, necesitamos una base única desde la cual ejecutar y mantener la aplicación web, la API y el worker.

Criterios de Aceptación:

- El workspace usa `pnpm` e incluye `apps/web`, `apps/api`, `apps/worker`, `packages/contracts` y `packages/config`.
- La aplicación web usa Next.js App Router con Tailwind CSS y la base de shadcn/ui.
- La API usa NestJS y el worker puede arrancar como proceso independiente.
- Cada aplicación compila por separado y desde la raíz del repositorio.
- El lockfile y las versiones de herramientas quedan versionados.

### 2

Título: Configurar el entorno local con PostgreSQL

Descripción: Como desarrollador, quiero levantar las dependencias locales de forma repetible para comenzar a trabajar sin configurar servicios manualmente.

Criterios de Aceptación:

- PostgreSQL puede iniciarse y detenerse mediante Docker desde el repositorio.
- Cada proceso valida sus variables de entorno al arrancar y falla con un mensaje claro si falta una obligatoria.
- Existe una plantilla de variables sin secretos y las variables del navegador no exponen credenciales.
- Un entorno limpio puede quedar operativo siguiendo un único procedimiento documentado.

### 3

Título: Preparar migraciones reproducibles con Prisma

Descripción: Como equipo de desarrollo, queremos evolucionar la base de datos de forma segura y comprobar cada cambio desde una base vacía.

Criterios de Aceptación:

- Prisma queda conectado al PostgreSQL local mediante configuración validada.
- Las migraciones se ejecutan mediante comandos explícitos y nunca al iniciar la aplicación.
- Existe un flujo automatizado para crear, aplicar y verificar migraciones en desarrollo y pruebas.
- Una base vacía puede reproducir el esquema completo sin pasos manuales.
- Las pruebas de integración usan PostgreSQL real y una base aislada.

### 4

Título: Establecer el contrato base de la API v1

Descripción: Como consumidor de la plataforma, quiero respuestas y errores consistentes para poder usar la API de forma predecible.

Criterios de Aceptación:

- Todos los endpoints iniciales se publican bajo `/api/v1`.
- Las entradas se validan con esquemas Zod estrictos y rechazan campos de seguridad desconocidos.
- Los errores siguen el contrato con `code`, `message`, `fieldErrors` y `correlationId`.
- Cada solicitud recibe un identificador de correlación seguro.
- OpenAPI documenta el endpoint de ejemplo y sus respuestas válidas y de error.

### 5

Título: Automatizar los controles de calidad del repositorio

Descripción: Como equipo de desarrollo, queremos detectar regresiones antes de integrar cambios para mantener estable la base del producto.

Criterios de Aceptación:

- Existen comandos raíz para formato, lint, tipos, pruebas y compilación.
- La validación automatizada ejecuta los controles para web, API, worker y paquetes compartidos.
- Las pruebas de integración levantan PostgreSQL real y verifican las migraciones.
- Un control fallido produce una salida clara y detiene la validación.
- Ningún secreto o archivo local sensible forma parte de los artefactos versionados.

### 6

Título: Solicitar el registro de una cuenta

Descripción: Como nuevo usuario, quiero registrar mi email para recibir una verificación y comenzar a usar la plataforma de forma segura.

Criterios de Aceptación:

- El formulario y la API aceptan un email válido y lo normalizan de forma consistente.
- La respuesta no revela si el email ya pertenece a una cuenta.
- La solicitud crea un token hasheado, de un solo uso y con vencimiento.
- Un mismo email corresponde a una única identidad global.
- La solicitud válida deja preparado un email de verificación sin enviarlo dentro de la transacción.

### 7

Título: Verificar el email y establecer la contraseña

Descripción: Como nuevo usuario, quiero confirmar mi email y definir una contraseña para activar mi identidad.

Criterios de Aceptación:

- Un token válido verifica únicamente el email para el cual fue emitido.
- El token se consume una sola vez y los tokens vencidos o inválidos muestran un error seguro.
- La contraseña se guarda con un hash resistente y parámetros configurables.
- Una cuenta no verificada no puede iniciar sesión.
- La pantalla confirma el resultado y ofrece continuar al acceso o al alta de organización.

### 8

Título: Iniciar sesión con una sesión opaca

Descripción: Como usuario verificado, quiero iniciar sesión sin exponer mis credenciales ni permisos en el navegador.

Criterios de Aceptación:

- El usuario puede acceder con email canonizado y contraseña válida.
- La sesión se guarda en el servidor y la cookie contiene solo un identificador aleatorio.
- El identificador de sesión rota al autenticar correctamente.
- La cookie no contiene roles, permisos ni datos de organización.
- Las credenciales inválidas producen una respuesta genérica y auditable.

### 9

Título: Administrar las sesiones activas

Descripción: Como usuario, quiero cerrar mi sesión o revocar otros accesos para mantener el control de mi cuenta.

Criterios de Aceptación:

- El usuario puede cerrar la sesión actual desde la web.
- El usuario puede consultar y revocar sus otras sesiones activas sin ver secretos.
- Una sesión revocada deja de autorizar solicitudes inmediatamente.
- Las sesiones tienen vencimiento y no pueden reutilizarse después de expirar.
- El cierre y la revocación quedan registrados sin almacenar el identificador completo de sesión.

### 10

Título: Recuperar una contraseña olvidada

Descripción: Como usuario, quiero restablecer mi contraseña mediante mi email para recuperar el acceso de forma segura.

Criterios de Aceptación:

- La solicitud de recuperación no revela si existe una cuenta para el email indicado.
- El enlace usa un token hasheado, de un solo uso y con vencimiento.
- Solo una contraseña que cumpla la política puede reemplazar la anterior.
- Un restablecimiento exitoso revoca todas las sesiones existentes del usuario.
- El resultado queda auditado sin guardar el token ni la contraseña.

### 11

Título: Proteger las mutaciones autenticadas

Descripción: Como usuario, quiero que las acciones realizadas con mi sesión estén protegidas contra solicitudes originadas por terceros.

Criterios de Aceptación:

- Toda mutación con cookie exige un `Origin` permitido exacto y un token CSRF ligado a la sesión.
- `GET`, `HEAD` y `OPTIONS` no producen cambios de estado.
- Las cookies usan `HttpOnly`, `SameSite=Lax` y `Secure` fuera del entorno local.
- CORS con credenciales acepta solo los orígenes configurados y nunca usa `*`.
- Login, registro y recuperación aplican límites de solicitudes con respuesta `429`.

### 12

Título: Enviar emails de identidad de forma confiable

Descripción: Como usuario, quiero recibir una sola copia válida de cada email de verificación o recuperación aunque el proveedor tarde o la plataforma reintente.

Criterios de Aceptación:

- Cada entrega se persiste antes de contactar a Resend y se clasifica como mensaje de identidad.
- El destinatario, propósito, plantilla, versión y contenido quedan congelados para los reintentos.
- Los reintentos usan la misma clave de idempotencia y el mismo contenido dentro de la ventana de 24 horas.
- Un fallo de Resend no revierte el registro, la recuperación ni otra transacción ya confirmada.
- Un resultado ambiguo fuera de la ventana automática queda visible para revisión manual y no se reenvía solo.

### 13

Título: Registrar los eventos de entrega de Resend

Descripción: Como operador, quiero conocer el estado confiable de los emails de identidad sin que eventos repetidos o desordenados alteren su historial.

Criterios de Aceptación:

- La firma se verifica sobre el cuerpo crudo antes de procesar el evento.
- Cada evento válido se guarda una sola vez y de forma append-only.
- Los callbacks duplicados producen el mismo resultado sin repetir una transición.
- Un evento fuera de orden no hace retroceder el estado derivado de la entrega.
- Las firmas inválidas se rechazan y se registran sin exponer el contenido sensible.

### 14

Título: Crear una organización pendiente desde plataforma

Descripción: Como superadministrador, quiero crear una organización y convocar a su primer administrador sin acceder a sus futuros datos de negocio.

Criterios de Aceptación:

- Solo un actor de plataforma autorizado puede iniciar el alta.
- La organización se crea en estado `PENDING_ACTIVATION`.
- La misma transacción crea la invitación inicial con el rol raíz solicitado, la auditoría y el evento de salida.
- El actor de plataforma no recibe membresía ni acceso a datos internos de la organización.
- Un fallo en cualquier parte deja la operación completa sin cambios parciales.

### 15

Título: Activar una organización con la invitación inicial

Descripción: Como primer administrador invitado, quiero aceptar mi invitación para activar la organización y comenzar a configurarla.

Criterios de Aceptación:

- La aceptación exige una identidad verificada con el mismo email canonizado de la invitación.
- La invitación debe estar pendiente, vigente y conservar roles válidos al momento de aceptar.
- Invitación, membresía raíz, activación, auditoría y evento de salida se confirman en una sola transacción.
- Dos aceptaciones concurrentes producen una sola membresía y una sola activación.
- Una invitación inicial consumida, vencida o revocada no puede reutilizarse.

### 16

Título: Autorregistrar una organización activa

Descripción: Como usuario verificado, quiero crear mi propia organización y quedar como administrador para empezar sin intervención de plataforma.

Criterios de Aceptación:

- El formulario solicita únicamente los datos básicos necesarios para crear la organización.
- Organización activa, configuración inicial, rol raíz, membresía, auditoría y evento de salida se crean atómicamente.
- Dos envíos concurrentes con la misma intención devuelven un único resultado sin duplicados.
- El usuario queda dentro del nuevo contexto de organización con una revisión vigente.
- El flujo no crea planes, límites ni cobros de suscripción.

### 17

Título: Administrar invitaciones de miembros

Descripción: Como administrador, quiero invitar miembros con roles definidos y controlar invitaciones pendientes, vencidas o revocadas.

Criterios de Aceptación:

- Solo una organización `ACTIVE` puede emitir o aceptar invitaciones ordinarias.
- Cada invitación usa email canonizado, token hasheado de un uso, vencimiento y estados `PENDING`, `ACCEPTED`, `REVOKED` o `EXPIRED`.
- La aceptación exige el mismo email verificado, vuelve a validar los roles solicitados y aplica límites de solicitudes.
- Una invitación obsoleta puede revocarse y reemitirse sin reutilizar el token anterior.
- Aceptar dos veces no crea más de una membresía para el usuario y la organización.

### 18

Título: Cambiar el contexto activo de organización

Descripción: Como usuario de varias organizaciones, quiero elegir en cuál estoy trabajando sin que una pestaña antigua pueda guardar datos en el contexto equivocado.

Criterios de Aceptación:

- El usuario puede listar y seleccionar únicamente organizaciones con membresía activa.
- La sesión conserva el identificador de la organización activa y una revisión de contexto.
- Cada cambio de organización incrementa la revisión sin confiar en un `organizationId` del formulario.
- Una mutación con revisión obsoleta responde `409 ORGANIZATION_CONTEXT_CHANGED`.
- La solicitud rechazada no crea dominio, auditoría ni eventos en ninguna organización.

### 19

Título: Configurar el perfil y la zona horaria de la organización

Descripción: Como administrador, quiero mantener los datos operativos de mi organización y definir la zona usada para sus fechas de negocio.

Criterios de Aceptación:

- Se pueden editar nombre legal y comercial, RUC opcional, dirección, contactos y prefijo de recibos.
- La zona horaria acepta únicamente identificadores IANA válidos y comienza con `America/Asuncion`.
- Cada comando resuelve una sola `businessDate` y conserva la revisión de zona utilizada.
- Un cambio de zona se registra desde el siguiente mes calendario, que en este incremento equivale al siguiente mes abierto, y no modifica revisiones previas.
- Los cambios quedan auditados sin exponer datos sensibles innecesarios.

### 20

Título: Suspender y reactivar una organización

Descripción: Como superadministrador, quiero detener temporalmente el uso de una organización conservando sus datos y reactivarla de forma controlada.

Criterios de Aceptación:

- Solo plataforma puede cambiar una organización entre `ACTIVE` y `SUSPENDED`.
- Durante la suspensión se bloquean sesiones de negocio, portal, cargas, exportaciones y nuevos mensajes salientes.
- Auditoría, callbacks válidos, integridad y tareas internas permitidas pueden continuar.
- La reactivación incrementa la revisión operativa para obligar a revalidar sesiones y trabajo retenido.
- Cada transición exige motivo, queda auditada y no elimina datos.

### 21

Título: Administrar membresías de la organización

Descripción: Como administrador, quiero consultar, suspender o revocar miembros para retirar accesos de forma inmediata.

Criterios de Aceptación:

- Existe como máximo una membresía por usuario y organización.
- Los estados permitidos son `ACTIVE`, `SUSPENDED` y `REVOKED`.
- Una suspensión o revocación impide nuevas solicitudes autorizadas inmediatamente.
- Roles y estado se vuelven a consultar y no se confían desde la cookie.
- Los cambios quedan auditados dentro de la organización.

### 22

Título: Configurar roles y permisos

Descripción: Como administrador, quiero crear roles ajustados a mi equipo usando únicamente las acciones permitidas por la plataforma.

Criterios de Aceptación:

- Los permisos forman un catálogo inmutable del sistema y los roles pertenecen a una sola organización.
- La organización recibe plantillas editables de administrador, operador, cobranzas y mantenimiento.
- El acceso efectivo es la unión de los permisos de los roles activos y se deniega por defecto.
- No existen permisos directos, denegaciones explícitas ni comodines.
- Crear o modificar un rol queda auditado y no afecta a otra organización.

### 23

Título: Impedir elevaciones y conservar un administrador raíz

Descripción: Como organización, quiero evitar que un miembro conceda privilegios que no posee o deje al equipo sin un administrador principal.

Criterios de Aceptación:

- Solo quien posee completamente la capacidad raíz puede concederla o modificarla.
- Toda organización activa conserva al menos una membresía raíz activa.
- Dos revocaciones o cambios concurrentes no pueden eliminar al último administrador raíz.
- Campos manipulados para asignar permisos controlados por el servidor se rechazan.
- Una operación rechazada no deja roles, membresías, auditoría ni eventos parciales.

### 24

Título: Separar los planos y principales de autorización

Descripción: Como usuario, quiero que mis permisos de plataforma, equipo u propietario nunca se mezclen accidentalmente.

Criterios de Aceptación:

- Cada endpoint declara explícitamente el plano `PLATFORM`, `INTERNAL` u `OWNER`.
- El principal se resuelve como identidad, actor de plataforma, membresía interna o job del sistema; el plano `OWNER` exige un grant explícito y permanece denegado hasta que el Incremento 1 lo introduzca.
- Un actor de plataforma no accede a datos del tenant sin una membresía interna válida.
- Los permisos internos no habilitan el plano de propietario y las coincidencias de email nunca conceden ese acceso.
- No existe impersonación y un plano no configurado se deniega por defecto.

### 25

Título: Aplicar aislamiento estricto entre organizaciones

Descripción: Como cliente, quiero que ninguna otra organización pueda descubrir, consultar o modificar mis datos.

Criterios de Aceptación:

- Toda fila del tenant incluye `organizationId` no nulo y las relaciones relevantes usan claves foráneas compuestas.
- Lecturas, escrituras, búsquedas, conteos, agregaciones y paginación aplican el alcance antes de permisos y joins.
- La organización activa proviene de la sesión y cualquier campo de alcance enviado por el cliente se rechaza.
- Un identificador ajeno y uno inexistente producen el mismo `404`; un recurso visible sin permiso produce `403`.
- Pruebas con dos organizaciones verifican que tampoco se filtran totales, metadatos ni respuestas de caché.

### 26

Título: Procesar comandos sensibles con idempotencia

Descripción: Como usuario, quiero poder reintentar una acción sensible sin crear organizaciones, invitaciones u otros resultados duplicados.

Criterios de Aceptación:

- La clave se limita por organización, actor y tipo de comando.
- Se guarda una huella canónica del contenido junto con el resultado confirmado.
- La misma clave y huella devuelve el resultado original sin repetir efectos.
- La misma clave con otro contenido responde `409 IDEMPOTENCY_KEY_REUSED`.
- Un rechazo anterior al commit no consume la clave y una clave nueva no evita restricciones naturales del dominio.

### 27

Título: Proteger mutaciones concurrentes y revocaciones

Descripción: Como usuario, quiero que una edición simultánea o una revocación de acceso no permita confirmar información obsoleta.

Criterios de Aceptación:

- Los agregados editables usan una versión y las mutaciones aceptan `expectedVersion`.
- Una versión obsoleta devuelve `409` sin sobrescribir cambios ajenos.
- Organización, principal, permisos y revisión de contexto se vuelven a comprobar dentro de la transacción.
- Una revocación confirmada antes del commit hace fallar la mutación completa.
- Los recursos múltiples se bloquean en un orden estable para evitar interbloqueos evitables.

### 28

Título: Registrar una auditoría append-only

Descripción: Como administrador autorizado, quiero consultar quién realizó cada acción sensible sin exponer secretos ni permitir alterar el historial.

Criterios de Aceptación:

- Cada evento declara alcance de plataforma u organización, actor tipado, acción, entidad, instante y correlación.
- Los cambios antes y después usan una lista permitida y excluyen contraseñas, tokens, sesiones y contenido completo.
- Los eventos no se pueden editar ni eliminar desde la aplicación.
- Un usuario autorizado puede buscar por actor, acción, entidad y rango de fechas.
- Un reintento idempotente no crea un segundo evento para la misma transición.

### 29

Título: Guardar eventos en un outbox transaccional

Descripción: Como operador, quiero que cada efecto posterior quede registrado junto con la acción que lo originó para no perderlo ni ejecutarlo antes del commit.

Criterios de Aceptación:

- El evento incluye organización, agregado, versión, correlación, causación y clave semántica.
- Dominio, idempotencia, auditoría y outbox se confirman o revierten en una sola transacción.
- Los eventos son inmutables y no se eliminan al procesarlos.
- Ninguna llamada externa ocurre dentro de la transacción de negocio.
- Repetir el comando confirmado no crea otro evento semánticamente equivalente.

### 30

Título: Convertir el outbox en jobs persistentes

Descripción: Como operador, quiero que el worker reciba trabajos durables que sobrevivan reinicios sin depender de Redis.

Criterios de Aceptación:

- La cola se almacena en PostgreSQL y no requiere un servicio de mensajería adicional.
- El dispatcher reclama eventos con `FOR UPDATE SKIP LOCKED` dentro de una transacción corta.
- Dos dispatchers concurrentes crean un solo job por clave semántica y generación.
- Un reinicio entre reclamo y despacho no pierde el evento ni crea un efecto duplicado.
- El estado pendiente y la antigüedad del trabajo pueden consultarse de forma operativa.

### 31

Título: Ejecutar jobs con lease y fencing token

Descripción: Como operador, quiero que solo el worker vigente pueda completar un trabajo aunque otro proceso se detenga o pierda su lease.

Criterios de Aceptación:

- Cada reclamo asigna lease, fencing token y número de intento de forma atómica.
- El handler se ejecuta fuera de la transacción corta de reclamo.
- Heartbeat y finalización exigen el token vigente.
- Un worker con lease vencido no puede marcar el trabajo como exitoso después de que otro lo reclame.
- El handler usa principal `SYSTEM_JOB`, reabre el tenant y vuelve a validar suspensión y revisión del origen sin fabricar una membresía.

### 32

Título: Gestionar reintentos y reejecuciones de jobs

Descripción: Como operador, quiero diagnosticar trabajos fallidos y reejecutarlos de forma controlada sin borrar su historia ni duplicar el resultado.

Criterios de Aceptación:

- Cada tipo de job define máximo de intentos y espera creciente.
- Los intentos y sus resultados se conservan de forma append-only.
- Al agotar intentos, el job queda visible como fallo terminal y no se reintenta solo.
- Una reejecución autorizada exige motivo y crea una generación enlazada con la misma clave semántica.
- Reintentar o reejecutar no duplica el efecto de negocio ya confirmado.

### 33

Título: Exponer salud y observabilidad de la plataforma

Descripción: Como operador, quiero distinguir una caída crítica de una dependencia degradada y localizar rápidamente solicitudes o jobs con problemas.

Criterios de Aceptación:

- Web, API y worker exponen comprobaciones de salud separadas.
- La disponibilidad de PostgreSQL determina readiness; una caída de Resend se informa como degradación sin bloquear operaciones locales.
- Los logs estructurados incluyen servicio, ruta, correlación y organización anonimizada cuando corresponda.
- Existen métricas de latencia, errores, conexiones, antigüedad de cola, intentos, leases y fallos del proveedor.
- Quedan definidas alertas para cola envejecida, leases vencidos, dead letters, entregas ambiguas y respaldos fallidos.

### 34

Título: Probar respaldo y restauración sin egress

Descripción: Como operador, quiero restaurar PostgreSQL sin reenviar efectos externos antiguos y con objetivos claros de pérdida y recuperación.

Criterios de Aceptación:

- El procedimiento define PITR con objetivo `RPO <= 15 min`, `RTO <= 8 h`, respaldo diario cifrado y retención mínima de 30 días.
- Toda restauración inicia aislada, sin egress y con un `restoreEpoch` nuevo.
- Outbox, jobs y entregas anteriores quedan en `RESTORE_HOLD`.
- Los jobs internos solo se liberan tras comprobar idempotencia; los efectos externos requieren reconciliación o liberación auditada.
- Una prueba documentada restaura una copia, verifica integridad y demuestra que no sale ningún mensaje pendiente automáticamente.

### 35

Título: Validar la puerta de aceptación del Incremento 0

Descripción: Como responsable del producto, quiero evidencia reproducible de que la plataforma segura está lista antes de comenzar la cartera.

Criterios de Aceptación:

- Las pruebas con PostgreSQL real cubren autorregistro e invitación concurrentes, contexto obsoleto, último administrador y revocación durante una mutación.
- Dos organizaciones intentan accesos cruzados en lecturas, escrituras, listados, conteos y caché sin revelar datos ni metadatos.
- Las pruebas cubren lease vencido, worker antiguo, reejecución, suspensión, reactivación, restauración en hold, CSRF, origen y campos controlados por servidor.
- Los flujos web principales funcionan con teclado y desde 360 px sin depender solo del color para comunicar estados.
- OpenAPI, variables de entorno, migraciones, operación del worker y recuperación quedan documentados y la validación completa pasa desde un entorno limpio.

## Orden de ejecucion

1. Plataforma local: tickets 1 a 5.
2. Sustrato transaccional: tickets 26 a 30.
3. Identidad, sesiones y email: tickets 6 a 13.
4. Organizaciones y autorizacion: tickets 14 a 25.
5. Ejecucion segura de jobs: tickets 31 y 32.
6. Operacion, recuperacion y aceptacion: tickets 33 a 35.

Las dependencias concretas se agregaran en Linear durante la creacion. El orden no obliga a serializar tickets que puedan ejecutarse en paralelo sin compartir una invariante.
