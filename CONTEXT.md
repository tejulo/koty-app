# PLAN-DEPTO

Especificacion funcional y tecnica para la primera version de un sistema SaaS de administracion de alquileres.

| Dato | Valor |
| --- | --- |
| Estado | Diseno y casos frontera aprobados; listo para planificar el incremento 0 |
| Fecha | 2026-08-09 |
| Version objetivo | V1 web adaptable |
| Mercado inicial | Paraguay |
| Idioma inicial | Espanol (`es-PY`) |
| Moneda | Guarani paraguayo (`PYG`) |
| Zona horaria inicial | `America/Asuncion`, configurable por organizacion |
| Modelo | SaaS multiempresa |
| Arquitectura | Monolito modular con API y worker separados |

## 1. Resumen ejecutivo

PLAN-DEPTO sera un sistema para que propietarios individuales y empresas administradoras controlen, desde una unica fuente confiable, sus ubicaciones, unidades, contratos, reservas temporarias, cobros, gastos, incidencias y liquidaciones.

Una ubicacion podra contener una o muchas unidades. Cada unidad tendra un nombre editable, un tipo fisico configurable y una modalidad de alquiler que puede cambiar con el tiempo sin perder su historia. Por ejemplo, una unidad que hoy opera como alquiler temporario podra pasar a vivienda tradicional. La condicion "en venta" sera independiente y podra coexistir con un alquiler activo.

El nucleo del producto sera el control financiero operativo. El sistema diferenciara cargos generados, entradas de caja, cobros aplicados, saldos pendientes, gastos pagados y fondos retenidos. Los resultados se podran consultar por rango de fechas, propietario, ubicacion o unidad, separando devengado, caja registrada y caja atribuible.

V1 sera una aplicacion web adaptable. Una API REST versionada permitira agregar una aplicacion movil en V2 sin reemplazar el backend.

## 2. Objetivos

### 2.1 Objetivos principales

- Centralizar propiedades, personas, contratos, reservas, documentos y movimientos.
- Saber mes a mes cuanto se genero, cuanto se cobro, cuanto sigue pendiente y cuanto se gasto.
- Mostrar resultados por organizacion, propietario, ubicacion, unidad y rango de fechas.
- Mantener visibles las unidades desocupadas con ingreso cero en los reportes del periodo.
- Evitar reservas superpuestas y cargos periodicos duplicados.
- Preservar un historial auditable de cambios de modalidad, titularidad y movimientos financieros.
- Permitir que los propietarios consulten su cartera, descarguen documentos y aprueben gastos.
- Aislar completamente los datos de cada organizacion SaaS.

### 2.2 Criterios de exito de V1

- Todo movimiento financiero confirmado tiene origen, responsable, fecha, detalle e historial de correcciones.
- Los totales visibles en pantalla coinciden con los PDF generados con los mismos filtros.
- Un reporte puede explicar la diferencia entre ingreso devengado, entrada de caja, cobro aplicado, deuda y resultado atribuible.
- Una reejecucion de procesos automaticos no duplica cargos, recordatorios ni documentos.
- Ningun usuario puede consultar o modificar datos de otra organizacion.
- Los flujos principales funcionan correctamente desde 360 px de ancho y en escritorio.

## 3. Alcance de V1

### 3.1 Incluido

- SaaS multiempresa para propietarios individuales y administradoras.
- Alta de organizaciones por superadministrador y por autorregistro con email verificado.
- Usuarios internos con roles y permisos configurables.
- Portal de propietarios para consulta, descarga y aprobacion de gastos.
- Ubicaciones, unidades, tipos fisicos configurables y nombres editables.
- Copropiedad de unidades con porcentajes y vigencias.
- Modalidades tradicional, temporaria y comercial con historial.
- Marca de unidad en venta, compatible con alquileres activos.
- Contratos tradicionales y comerciales; cada contrato pertenece a una sola unidad y la unidad conserva contratos historicos no superpuestos.
- Cronograma pactado de importes durante el contrato.
- Mora manual o automatica segun configuracion.
- Calendario interno, bloqueos y reservas temporarias.
- Cargos, pagos manuales, aplicaciones de pago, saldos y recibos internos.
- Registro de facturas externas sin emision fiscal.
- Depositos de garantia como fondos retenidos.
- Incidencias, aprobaciones de propietario y gastos con detalle.
- Gastos de unidad y ubicacion, con imputacion opcional.
- Traslado total o parcial de un gasto al inquilino.
- Liquidaciones a propietarios sin comision automatica de administradora.
- Documentos generados desde plantillas y archivos adjuntos.
- Email mediante Resend y orquestacion de WhatsApp mediante un webhook firmado y desacoplado del proveedor.
- Reportes en pantalla y PDF.
- Carga manual e importacion CSV basica de ubicaciones, unidades y partes.
- Auditoria de acciones sensibles.

### 3.2 Fuera de alcance

- Gestion de prospectos, ofertas, escrituras o cierre de compraventas.
- Emision fiscal ante DNIT, SIFEN o e-Kuatia.
- Contabilidad general, plan de cuentas y asientos contables.
- Pasarela de pagos o movimiento de dinero desde la plataforma.
- Conciliacion bancaria.
- Calculo automatico de comisiones de administradora.
- Sincronizacion con Airbnb, Booking u otros canales.
- Firma electronica o digital dentro del sistema.
- Aplicacion movil nativa.
- Multimoneda y conversion de cotizaciones.
- Facturacion y cobro recurrente de la suscripcion SaaS.
- Importacion masiva de contratos y movimientos historicos.
- Gestion avanzada de inventario, ordenes de compra o mantenimiento preventivo.
- Integracion directa con una API especifica de WhatsApp; V1 entrega un webhook generico para conectar un bridge externo.

## 4. Actores y acceso

### 4.1 Superadministrador de plataforma

- Crea organizaciones y su primer administrador.
- Consulta y cambia el estado operativo de una organizacion.
- Puede suspender y reactivar una organizacion conservando sus datos.
- No accede por defecto a propiedades, contratos o finanzas de una organizacion.
- Para acceder a datos de negocio debe ser invitado como miembro de esa organizacion; esa incorporacion queda auditada.
- Gestiona la operacion SaaS, pero no suscripciones ni cobros de planes en V1.

### 4.2 Administrador de organizacion

- Configura identidad, catalogos, documentos, avisos y reglas de negocio.
- Invita usuarios y crea roles a partir de permisos disponibles.
- Controla las acciones de cada rol y las politicas de aprobacion.
- Puede cerrar y reabrir periodos con permiso especial y motivo obligatorio.

### 4.3 Miembro del equipo

- Accede solamente a las acciones habilitadas por sus roles.
- Los permisos se definen por accion, por ejemplo ver, crear, editar, confirmar, anular, aprobar, cerrar, exportar o administrar.
- La organizacion recibe plantillas iniciales de roles, pero puede crear y modificar sus propios roles.
- En V1 los miembros internos autorizados tienen alcance sobre toda la organizacion; no existen restricciones por ubicacion o unidad.
- Identidad, permisos y organizacion activa son controles separados: tener permiso para ver gastos nunca elimina el filtro de organizacion.

### 4.4 Propietario

- Mientras su titularidad esta vigente, ve la unidad y los registros autorizados cuyo periodo o fecha efectiva intersecta su titularidad.
- Al terminar su titularidad, conserva acceso solo a sus liquidaciones, movimientos atribuidos, documentos historicos dirigidos a el y decisiones de gasto ya materializadas a su cargo; no ve ocupacion, partes ni documentos posteriores.
- Consulta ocupacion, contratos, movimientos, gastos, incidencias, liquidaciones y documentos permitidos.
- Los importes propios se muestran segun su participacion; no se revelan liquidaciones privadas de otros copropietarios.
- Descarga reportes y PDF.
- Aprueba o rechaza gastos cuando forma parte de la politica de aprobacion aplicable.
- No modifica propiedades, contratos ni movimientos en V1.

### 4.5 Inquilino, huesped, garante y proveedor

- Se registran como partes del negocio, pero no inician sesion en V1.
- Pueden recibir documentos y notificaciones en los canales autorizados.

## 5. Glosario del dominio

| Termino | Definicion |
| --- | --- |
| Organizacion | Limite SaaS que contiene usuarios, configuracion y todos los datos de un cliente. |
| Ubicacion | Edificio, complejo, terreno o direccion que agrupa unidades. |
| Unidad | Bien individual operable, por ejemplo departamento, casa, duplex, cabana o salon. |
| Tipo fisico | Clasificacion configurable de una unidad. No define como se comercializa. |
| Modalidad | Forma de operacion de alquiler: tradicional, temporaria o comercial. Tiene vigencia historica. |
| Estado administrativo de unidad | Ciclo `SETUP`, `ACTIVE` o `ARCHIVED`; determina si la unidad esta completa y admite nuevas operaciones. |
| Estado operativo derivado | Disponibilidad, ocupacion o bloqueo calculados desde contratos, reservas, bloqueos y vigencia administrativa; no se edita directamente. |
| Parte | Persona fisica o juridica que puede actuar como propietario, inquilino, huesped, garante o proveedor. |
| Titularidad | Participacion porcentual de una parte propietaria sobre una unidad durante una vigencia. |
| Contrato | Acuerdo tradicional o comercial asociado a una sola unidad. |
| Reserva | Estadía temporaria asociada a una unidad y un intervalo de fechas. |
| Cargo | Importe exigible generado por alquiler, mora, servicio, gasto trasladado u otro concepto. |
| Pago | Fuente confirmada para cancelar deuda; puede ser cobro externo o aplicacion interna de un deposito. |
| Aplicacion de pago | Parte de un pago asignada a un cargo concreto. |
| Reembolso de pago | Salida de caja que devuelve saldo externo no aplicado; no es gasto ni borra la recepcion original. |
| Gasto | Egreso o costo documentado a nivel de unidad o ubicacion. |
| Deposito | Fondo recibido y retenido como garantia; no constituye ingreso de alquiler. |
| Incidencia | Problema o tarea de mantenimiento con responsables, estados, evidencias y gastos. |
| Liquidacion | Estado de cuenta confirmado para un propietario durante un periodo. |
| Criterio devengado | Considera cargos y gastos correspondientes al periodo, aunque no se hayan cobrado o pagado. |
| Entrada de caja | Pago o recepcion de deposito clasificado por la fecha efectiva en que se recibieron los fondos. |
| Cobro aplicado | Importe asignado a un cargo, clasificado por la fecha efectiva de la aplicacion. |
| Criterio de caja | Clasifica cada movimiento por su propia fecha efectiva: pagos por recepcion, aplicaciones por aplicacion, gastos por pago y devoluciones por salida. |
| Fecha civil | Fecha `YYYY-MM-DD` sin zona ni hora, interpretada segun las reglas de negocio de la organizacion. |
| Instante | Marca temporal UTC de un hecho tecnico, por ejemplo creacion, confirmacion o auditoria. |
| Fecha de referencia | Fecha civil `referenceDate` que determina origen economico, titularidad o servicio de un movimiento. |
| Fecha de contabilizacion | Fecha civil `postingDate` que determina el periodo donde se informa una correccion; normalmente coincide con la fecha de referencia, salvo ajustes de periodos cerrados. |

## 6. Modelo conceptual

```text
Organizacion
  |-- Miembros -- Usuario -- Roles -- Permisos
  |-- Partes
  |     |-- Propietarios -- Titularidades -- Unidad
  |     |-- Inquilinos/Garantes -- Contrato -- Unidad
  |     `-- Huespedes -- Reserva -- Unidad
  |-- Ubicaciones -- Unidades -- Historial de modalidad
  |-- Cargos -- Aplicaciones de pago -- Pagos
  |-- Gastos -- Detalles / Imputaciones / Aprobaciones
  |-- Depositos
  |-- Incidencias
  |-- Liquidaciones
  |-- Documentos
  `-- Auditoria / Trabajos asincronos / Notificaciones
```

### 6.1 Entidades principales

| Entidad | Responsabilidad y relaciones clave |
| --- | --- |
| `Organization` | Configuracion, branding, zona horaria, secuencias, catalogos y limite de aislamiento. |
| `User` | Identidad de acceso global por email. |
| `Membership` | Vincula usuario, organizacion, estado y roles. |
| `Invitation` | Invitacion de un solo uso que vincula email normalizado, organizacion, roles solicitados, vencimiento y estado. |
| `Role` / `Permission` | Autorizacion configurable por accion dentro de una organizacion. |
| `OwnerPortalGrant` | Vinculo explicito entre una membresia activa y una parte propietaria; nunca se infiere por email. |
| `Party` | Datos de persona fisica o juridica y sus roles de negocio. |
| `Location` | Agrupa unidades y recibe gastos generales. |
| `Unit` | Bien operable, codigo, nombre, tipo fisico, estado administrativo, `activatedDate` y `archivedDateExclusive`. |
| `UnitModalityPeriod` | Intervalo de vigencia de modalidad sin superposiciones. |
| `OwnershipShare` | Propietario, porcentaje y vigencia sobre una unidad. |
| `LeaseContract` | Contrato tradicional o comercial de una unidad. |
| `RentScheduleItem` | Importe pactado y vigencia dentro de un contrato. |
| `Booking` / `AvailabilityBlock` | Reserva temporaria o bloqueo de calendario. |
| `Charge` | Obligacion monetaria emitida con fecha de reconocimiento y periodo de servicio opcional. |
| `Payment` / `PaymentAllocation` | Cobro confirmado y distribucion fechada contra cargos. |
| `PaymentRefund` | Devolucion fechada de fondos externos disponibles. |
| `Expense` / `ExpenseLine` | Gasto y detalle de conceptos cuyo total debe cuadrar. |
| `ExpenseAllocation` | Imputacion financiera a unidad, propietario o inquilino. |
| `SecurityDeposit` / `DepositMovement` | Cuenta de garantia y movimientos de recepcion, aplicacion, devolucion o correccion. |
| `MaintenanceIssue` | Flujo de incidencia, aprobaciones y costos relacionados. |
| `OwnerStatement` | Instantanea de liquidacion por propietario y periodo. |
| `OwnerDisbursement` | Salida de caja registrada al pagar una liquidacion confirmada. |
| `FinancialPeriod` | Mes financiero abierto o cerrado que controla movimientos retroactivos y liquidaciones. |
| `UploadIntent` | Autorizacion temporal de carga con objeto staging, validacion, cuarentena y finalizacion idempotente. |
| `Document` | Metadatos, pertenencia, version y clave privada en Spaces. |
| `Notification` | Canal, destinatario, plantilla, estado e intentos de entrega. |
| `IdempotencyRecord` | Ambito, clave, huella canonica y resultado estable de un comando reintentable. |
| `OutboxEvent` / `Job` | Efecto posterior al commit y trabajo persistido con clave semantica, intentos, lease y fencing token. |
| `AuditEvent` | Actor, accion, entidad, cambios relevantes y correlacion. |

## 7. Reglas e invariantes

### 7.1 Aislamiento multiempresa

- Toda fila perteneciente a un tenant, salvo la propia raiz `Organization`, incluidas tablas de union, invitaciones, membresias, grants de portal, idempotencia, outbox, jobs, documentos y auditoria organizacional, debe incluir `organizationId` no nulo.
- La organizacion activa se obtiene de la sesion autenticada, nunca de un valor confiado del formulario.
- Toda consulta y mutacion debe aplicar el alcance de organizacion antes de evaluar permisos funcionales.
- Las relaciones entre filas del tenant deben usar claves foraneas compuestas `(organizationId, id)` que impidan referencias entre organizaciones incluso si se omite una validacion de aplicacion.
- Un identificador inexistente o perteneciente a otro alcance devuelve el mismo `404`; `403` se reserva para un recurso visible dentro del alcance cuando falta permiso para la accion.
- Busquedas, conteos, agregaciones, deteccion de duplicados, paginacion, exportaciones y caches aplican el alcance antes de unir o proyectar datos. Las respuestas privadas usan cache privada sin almacenamiento compartido.
- Toda mutacion critica vuelve a comprobar organizacion cuando corresponda, principal de autorizacion y revisiones relevantes dentro de la transaccion antes del commit. Los principales son `USER_IDENTITY`, `PLATFORM_ACTOR`, `INTERNAL_MEMBERSHIP`, `OWNER_GRANT` y `SYSTEM_JOB`; un job no inventa una membresia humana.
- Las pruebas automatizadas deben intentar accesos cruzados con identificadores validos de otra organizacion.

### 7.2 Dinero y fechas

- Todos los importes se guardan como enteros PYG; no se usan numeros de punto flotante.
- Los importes viajan por la API como cadenas decimales y se operan con enteros de precision arbitraria; nunca se convierten a `number` de JavaScript.
- V1 no convierte monedas ni acepta movimientos en una moneda distinta de PYG.
- Los campos terminados en `At` son instantes UTC tecnicos. Las fechas contractuales, financieras, periodos y noches se modelan como fechas civiles y usan nombres terminados en `Date`; no se convierten a UTC.
- Las vigencias se normalizan como intervalos semiabiertos `[fromDate, toDateExclusive)`. Un fin contractual legal inclusivo se compara internamente como el dia civil siguiente, nunca sumando 24 horas.
- Cada comando calcula una sola `businessDate` con la zona IANA vigente y la conserva durante toda la transaccion. La configuracion de zona se versiona por mes efectivo; un cambio es prospectivo desde el primer dia del siguiente mes abierto y nunca reclasifica historia.
- Las participaciones se guardan como partes por millon: `1.000.000 = 100 %`. Todo reparto PYG usa mayores restos y desempate por identificador inmutable; las lineas materializadas conservan el total original y exponen el ajuste entero.
- Todo cargo tiene `recognitionDate`. El devengado, periodo financiero y titularidad se determinan por esa fecha.
- Para alquiler mensual `recognitionDate` es el inicio del periodo de servicio; para reserva es check-in; para mora, servicio o gasto trasladado es la fecha efectiva del hecho que lo origina.
- V1 reconoce el cargo completo en `recognitionDate` y no prorratea automaticamente intervalos que cruzan meses. Si el acuerdo exige reparto, se emiten cargos separados.

### 7.3 Historia e inmutabilidad

- Los registros financieros confirmados no se eliminan ni se sobrescriben para ocultar su valor original.
- Todo hecho financiero fuente guarda una magnitud estrictamente positiva; su tipo o direccion expresa el signo economico. Los totales derivados pueden ser cero o negativos.
- Una correccion financiera usa un evento inverso o ajuste enlazado, con fecha de referencia original y fecha de contabilizacion. No cambia retrospectivamente el estado ni excluye el hecho original.
- Cada familia financiera define una proyeccion con signo para reportes. El importe almacenado sigue positivo; recibos, debitos o entradas aportan segun su direccion, y creditos, salidas o efectos inversos aportan el signo contrario. Las correcciones de caja se clasifican por su propia fecha de contabilizacion.
- Los contratos, plantillas, titularidades y modalidades conservan intervalos de vigencia.
- Un cambio de titularidad o modalidad no recalcula cargos, gastos ni liquidaciones ya confirmados.
- Los documentos generados guardan la version de plantilla y los datos usados al momento de generacion.

Los ciclos financieros obligatorios son:

- Un cargo pasa de borrador a emitido; un borrador puede descartarse. Un cargo emitido permanece y se corrige mediante creditos enlazados. Abierto, parcialmente pagado, pagado, vencido y corregido son estados derivados de sus efectos, aplicaciones y vencimiento.
- Un pago externo pasa de borrador a confirmado o anulado. Al confirmar se fijan importe y fecha efectiva de recepcion.
- Una fuente interna por deposito se crea confirmada, sin entrada de caja, con fecha efectiva igual a su aplicacion.
- Una aplicacion confirmada permanece inmutable. Una reversion total o parcial es otro evento fechado y enlazado; `ACTIVE`, `PARTIALLY_REVERSED` y `FULLY_REVERSED` son estados derivados.
- Un reembolso de pago externo pasa de borrador a confirmado o anulado. Al confirmar fija importe y `refundedDate`.
- Un movimiento de deposito pasa de borrador a confirmado. Una correccion confirmada usa otro movimiento enlazado; su tipo determina si aumenta o reduce el saldo retenido.
- Un gasto conserva `incurredDate` desde que pasa a incurrido y `paidDate` desde que pasa a pagado. Pagarlo no elimina su condicion de incurrido.
- Solamente estados emitidos o confirmados participan en reportes; los estados derivados no sustituyen el historial de movimientos.

### 7.4 Titularidad

- Una unidad puede tener uno o varios propietarios.
- La composicion completa de propietarios es un agregado temporal que se reemplaza atomica y prospectivamente bajo bloqueo de la unidad; no se edita participacion por participacion.
- Una unidad `ACTIVE` debe resolver exactamente `1.000.000` partes por millon en cada fecha de su vigencia. Huecos o sumas incompletas solo se permiten en `SETUP`.
- Una parte aparece como maximo una vez por composicion y toda participacion es positiva. No pueden existir superposiciones o huecos que violen el total.
- Cargos y gastos que alimentan liquidaciones conservan una instantanea de la participacion aplicable.
- La participacion de un cargo se determina por `recognitionDate`; para alquiler mensual coincide con el inicio del periodo de servicio.
- Una composicion ya usada por un cargo emitido, gasto incurrido, aprobacion o audiencia documental no se reescribe. Una correccion retroactiva se representa mediante ajustes separados.
- Un acuerdo que requiera prorrateo dentro del periodo se representa mediante cargos o ajustes separados.
- La participacion de un gasto se determina por `incurredDate`.
- Una imputacion posterior usa una `allocationEffectiveDate` que por defecto coincide con `incurredDate`; nunca usa la fecha en que el usuario termino de procesarla.
- Elegir "todas las unidades activas" materializa las unidades existentes en `allocationEffectiveDate`, de modo que altas o bajas posteriores no cambian el resultado.

### 7.5 Disponibilidad

- Una reserva confirmada ocupa el intervalo `[check-in, check-out)`; permite salida y nueva entrada el mismo dia.
- Un contrato tradicional o comercial ocupa internamente `[startDate, endDate + 1 dia civil)` y conserva su prefijo historicamente ocupado al finalizar o rescindirse.
- Los borradores, contratos `ANNULLED`, reservas `CANCELLED` o `NO_SHOW` y bloqueos cancelados antes de iniciar no reclaman fechas. Contratos activados o terminados, reservas confirmadas o con check-in y bloqueos iniciados conservan el reclamo efectivo completo o su prefijo historico segun la transicion.
- Una unidad puede tener varios contratos historicos, pero no dos reclamos de contrato, reserva o bloqueo superpuestos.
- Toda reserva debe quedar completamente contenida en modalidad temporaria y todo contrato en su modalidad tradicional o comercial. Un bloqueo es neutral y puede atravesar un cambio de modalidad.
- Toda mutacion que cambie disponibilidad, modalidad, archivo, cancelacion o terminacion bloquea primero la misma fila `Unit`, relee estado y conflictos, y confirma en una sola transaccion.
- Para varias unidades se bloquea por identificador ascendente. No se realizan llamadas externas dentro de la transaccion.

### 7.6 Idempotencia

- Un cargo periodico se identifica de manera unica por contrato, periodo y concepto.
- Las claves naturales usan propositos estables del sistema y no etiquetas configurables. Renombrar un concepto o plantilla no permite duplicar el hecho.
- Una notificacion automatica se identifica por ocurrencia de evento, identidad y destino normalizado del destinatario, canal y proposito.
- Los comandos sensibles aceptan una clave de idempotencia cuando puedan repetirse por red o worker.
- La clave se limita por organizacion, actor o membresia y comando. Se guarda una huella canonica: misma clave y huella devuelve el resultado original; otra huella devuelve `409 IDEMPOTENCY_KEY_REUSED`.
- La reserva de clave, mutacion, auditoria y outbox confirman atomicamente. Un rechazo anterior al commit no consume la clave.
- `expectedVersion` controla ediciones concurrentes y es independiente de idempotencia.
- Reintentar una operacion no puede duplicar cargos, pagos, liquidaciones, PDF ni mensajes.

### 7.7 Periodos financieros

- Cada organizacion tiene un unico periodo por mes calendario, identificado por `YYYY-MM`; los periodos no se superponen.
- Un periodo solo puede cerrarse cuando termino su mes civil. Desde el primer mes financiero de la organizacion se cierra en orden cronologico y se reabre en orden inverso; los meses intermedios vacios se materializan.
- Un periodo abierto admite hechos cuya fecha de contabilizacion cae dentro del mes. Incluye cargos y ajustes, pagos y correcciones, aplicaciones y reversiones, reembolsos y correcciones, movimientos de deposito, gastos por `incurredDate` y `paidDate`, atribuciones tardias y desembolsos a propietarios.
- El cierre evalua la fecha efectiva de cada movimiento, no la fecha original de su entidad. Un gasto incurrido en agosto puede pagarse en septiembre abierto sin modificar su importe ni `incurredDate` de agosto.
- Cada confirmacion obtiene o crea y bloquea su periodo antes de confirmar; el cierre toma el mismo bloqueo. O el movimiento entra completo antes del cierre o falla con conflicto despues.
- Los reportes pueden consultar meses abiertos o cerrados, pero una liquidacion confirmada solo usa un periodo cerrado.
- Si no existe una liquidacion pagada, un usuario autorizado puede reabrir el mes. Las liquidaciones confirmadas quedan marcadas para reemision y sus versiones anteriores se conservan.
- Si alguna liquidacion del mes tiene un desembolso confirmado, el periodo no se reabre para alterar su neto; la correccion se registra como ajuste enlazado en el periodo abierto que contiene la `businessDate` del comando.
- Un movimiento omitido de un mes cerrado no puede retrofecharse sin reapertura. Si el mes no puede reabrirse, se registra con `postingDate = businessDate` en su periodo abierto y referencia fecha y origen reales.
- Un movimiento atribuible a propietario puede aparecer en una sola linea de liquidacion activa; una restriccion evita volver a liquidarlo.

### 7.8 Visibilidad historica del propietario

- El acceso de portal exige un `OwnerPortalGrant` explicito entre membresia activa y parte propietaria. Coincidencias de email, telefono o documento nunca conceden acceso.
- La visibilidad financiera se decide por las instantaneas de participacion y las lineas atribuidas al propietario.
- La vista operativa actual de una unidad exige una titularidad vigente.
- Una titularidad finalizada no habilita datos de inquilinos, huespedes, incidencias o contratos posteriores.
- Las respuestas de portal usan proyecciones propias y no reutilizan DTO internos; nunca exponen datos privados de copropietarios ni contactos, documentos u observaciones internas de inquilinos o huespedes.
- Cada documento materializa audiencia por partes y fecha o intervalo efectivo al crearse; no recalcula "propietarios afectados" con la titularidad actual.
- Un propietario historico con grant vigente ve un documento solo si fue incluido en su audiencia y la fecha efectiva intersecta su titularidad, o si pertenece a una liquidacion propia. Revocar el grant elimina tambien el acceso historico futuro sin borrar decisiones anteriores.

### 7.9 Casos frontera aprobados

Esta seccion es normativa. Cada decision responde la pregunta indicada con la opcion recomendada durante la revision. Si una regla local admite dos lecturas, prevalece la decision `BND-*` y el plan del incremento debe convertirla en restricciones, transiciones y pruebas concretas.

#### 7.9.1 Convenciones transversales

| ID | Caso frontera | Decision aprobada para V1 |
| --- | --- | --- |
| `BND-001` | Limites de fechas contiguas | Todas las vigencias usan fechas civiles e intervalos `[inicio, fin exclusivo)`. El fin legal inclusivo de un contrato se normaliza al dia civil siguiente. Dos intervalos se superponen solo si `a.inicio < b.fin` y `b.inicio < a.fin`; un intervalo vacio se rechaza. |
| `BND-002` | Medianoche y cambio de zona | Cada comando fija una sola `businessDate` y la revision de zona IANA usada. Las revisiones tienen mes efectivo; un cambio entra en vigor al inicio del siguiente mes abierto y no modifica fechas, periodos ni documentos historicos. |
| `BND-003` | Precision monetaria y porcentual | Importes y porcentajes nunca usan punto flotante. Los repartos se materializan con mayores restos, desempate por ID inmutable y suma exacta en cada nivel. Pantalla, liquidacion y PDF suman esas lineas; no recalculan redondeos. |
| `BND-004` | Correccion de un hecho confirmado | El hecho original permanece visible. La correccion es un evento enlazado de direccion inversa con su propia fecha de contabilizacion; si el periodo original no puede reabrirse, usa `postingDate = businessDate`, exige abierto ese periodo y conserva fecha de referencia e instantanea originales. |
| `BND-005` | Operacion que cruza modulos | Reservar fechas y emitir cargos, aplicar deposito, trasladar gasto, confirmar pago con aplicaciones y confirmar liquidacion son coordinaciones sincronas en una transaccion. Outbox se usa solo para efectos posteriores al commit. |
| `BND-006` | Ediciones y confirmaciones concurrentes | Cada agregado tiene version. `expectedVersion` evita perdida de actualizaciones; los bloqueos protegen invariantes de saldo, calendario, titularidad y periodo. Los recursos multiples se bloquean por tipo e ID en orden estable. |
| `BND-007` | Reintento de un comando | Idempotencia y control optimista son independientes. Misma clave y huella devuelve el resultado original; misma clave con otro contenido devuelve `409`; una nueva clave no elude una clave natural del dominio. |
| `BND-008` | Recurso de otro tenant | El alcance se aplica antes de permiso, validacion semantica, joins, conteos y cache. Un ID ajeno y uno inexistente producen el mismo `404`; un recurso visible sin permiso produce `403`. Los esquemas rechazan campos de seguridad desconocidos o controlados por el servidor. |
| `BND-009` | Auditoria de una mutacion sensible | Dominio, auditoria y outbox confirman juntos. La auditoria es append-only, usa diferencias permitidas, excluye secretos y distingue alcance de plataforma u organizacion y actor humano, portal o job. Un reintento idempotente no crea otro evento de transicion. |
| `BND-010` | Lectura asincrona mutable | Reportes, PDF, documentos y notificaciones congelan filtros, revisiones, datos resueltos, audiencia, locale, zona y versiones antes de encolarse. El worker procesa esa instantanea y vuelve a autorizar; no reconstruye contenido con el estado actual. |

#### 7.9.2 Organizaciones, identidad y acceso

| ID | Caso frontera | Decision aprobada para V1 |
| --- | --- | --- |
| `BND-IAM-01` | Organizacion sin primer administrador | Los estados son `PENDING_ACTIVATION`, `ACTIVE` y `SUSPENDED`. La creada por plataforma queda pendiente hasta aceptar la primera invitacion; el autorregistro crea organizacion, defaults, rol, membresia, auditoria y outbox atomicamente despues de verificar email. |
| `BND-IAM-02` | Uso durante suspension | Se bloquean sesiones de negocio, portal, cargas, URLs firmadas, exportaciones, PDF solicitados y mensajes salientes. Continuaran callbacks, auditoria, limpieza, respaldo, integridad y jobs contables deterministas para no alterar historia contractual. Al reactivar se reevalua la vigencia de trabajos retenidos. |
| `BND-IAM-03` | Un email en varias organizaciones | `User` es global y unico por email canonico; cada tenant posee `Membership`, no `User`. `Party` es identidad de negocio separada. Coincidir email, telefono, documento o RUC nunca crea acceso ni une identidades automaticamente. |
| `BND-IAM-04` | Invitacion vencida, repetida o con rol cambiado | La invitacion tiene email canonico, token hasheado de un uso, vencimiento y estados `PENDING`, `ACCEPTED`, `REVOKED`, `EXPIRED`. La invitacion inicial puede aceptarse en `PENDING_ACTIVATION` y activa la organizacion en la misma transaccion; las demas exigen organizacion `ACTIVE`. Toda aceptacion consume atomicamente, exige el mismo email y revalida roles y grants; una invitacion obsoleta se reemite. |
| `BND-IAM-05` | Revocacion inmediata | Existe una membresia por usuario y organizacion, con estados `ACTIVE`, `SUSPENDED`, `REVOKED`. Las sesiones son opacas, server-side, rotables y revocables; reset de contrasena revoca todas. Roles, grants y estado se consultan de nuevo, no se confian desde una cookie. |
| `BND-IAM-06` | Cambio de organizacion con pestanas antiguas | La sesion conserva organizacion activa y revision de contexto. Toda mutacion envia la revision esperada solo como asercion; si otra pestana cambio de tenant devuelve `409 ORGANIZATION_CONTEXT_CHANGED` y no crea datos en ningun tenant. |
| `BND-IAM-07` | Combinacion y elevacion de roles | Permisos son un catalogo inmutable del sistema; roles son del tenant y su efecto es la union de concesiones, con denegacion por defecto. V1 no tiene grants directos, denies ni comodines. Debe quedar al menos un administrador raiz activo y nadie puede conceder esa raiz sin poseerla completa. |
| `BND-IAM-08` | Usuario que es equipo y propietario | Cada endpoint declara plano `PLATFORM`, `INTERNAL` u `OWNER`; los permisos no se mezclan. Portal exige `OwnerPortalGrant` explicito. Superadministracion de plataforma no autoriza datos del tenant y no existe impersonacion en V1. |
| `BND-IAM-09` | Cambio de propietario o representante durante una aprobacion | La solicitud congela partes propietarias requeridas. Una decision es por `Party`, aunque tenga varios representantes; la primera decision terminal gana. Revocar grant impide decidir. Una transferencia futura no reescribe la audiencia; una correccion de titularidad, fecha, alcance o version que si la altera invalida y obliga a reevaluar. |
| `BND-IAM-10` | CSRF y origen | Toda mutacion con cookie exige `Origin` exacto permitido y token CSRF ligado a sesion. `GET`, `HEAD` y `OPTIONS` no mutan. Cookies usan `HttpOnly`, `Secure` fuera de local y `SameSite=Lax`; CORS con credenciales nunca usa `*`. |

#### 7.9.3 Partes, cartera, titularidad e importacion

| ID | Caso frontera | Decision aprobada para V1 |
| --- | --- | --- |
| `BND-PRT-01` | Unidad incompleta, ocupada o archivada | Solo persiste estado administrativo `SETUP`, `ACTIVE`, `ARCHIVED`, con transiciones terminales `SETUP -> ACTIVE -> ARCHIVED`, `activatedDate` y `archivedDateExclusive`. Ocupada, bloqueada, vacante y disponible son proyecciones. Una unidad `SETUP` no admite compromisos ni finanzas nuevas y no aparece como activa en reportes. |
| `BND-PRT-02` | Identidad y roles de una parte | `Party` es `PERSON` o `LEGAL_ENTITY`; propietario, inquilino, huesped, garante y proveedor se derivan de relaciones. El tipo solo cambia antes de tener referencias de negocio. |
| `BND-PRT-03` | Duplicados duros y blandos | Documento o RUC normalizado y tipado es unico por organizacion. Email y telefono normalizados son alertas blandas y pueden compartirse con resolucion explicita. Si identificadores apuntan a partes distintas se bloquea; fusionar partes referenciadas queda fuera de V1. |
| `BND-PRT-04` | Archivo de una parte con historia | No se archiva con titularidad vigente o futura, contrato activo, reserva futura o aprobacion pendiente. Archivada no recibe relaciones nuevas, pero permite cobrar, devolver, corregir y documentar relaciones previas. |
| `BND-PRT-05` | Codigos y secuencias concurrentes | `Location.code` es unico por organizacion y `Unit.code` por ubicacion, comparados de forma normalizada y no reutilizables. Las secuencias de nombres y recibos son monotonicas, unicas y pueden tener huecos; un reintento idempotente conserva numero y prefijo originales. |
| `BND-PRT-06` | Catalogo desactivado | Tipos fisicos y otros catalogos tienen codigo inmutable, etiqueta editable y estado habilitado. Desactivar conserva referencias historicas pero impide nuevas asignaciones. Cambiar tipo fisico de una unidad activa es una correccion auditada, no una historia temporal en V1. |
| `BND-PRT-07` | Cambio concurrente de copropiedad | Se reemplaza la composicion completa desde una fecha bajo bloqueo de la unidad. Una unidad activa mantiene 100 % continuo. Una composicion ya consumida por hechos confirmados no se reescribe; el ajuste usa la instantanea afectada. |
| `BND-PRT-08` | Cambio de modalidad con operaciones o bloqueo | Una unidad activa tiene una modalidad continua y unica. Contratos y reservas deben quedar completamente cubiertos por la modalidad compatible. Un bloqueo es neutral, puede cruzar el cambio y sigue impidiendo ocupacion. |
| `BND-PRT-09` | Archivo con compromisos o deuda | Archivar exige que ningun reclamo ocupe la fecha de archivo o el futuro y no cancela en cascada. Bloquea operaciones nuevas, pero permite cobros, reembolsos, ajustes, liquidaciones y documentos historicos. Una ubicacion se archiva solo cuando todas sus unidades lo estan. |
| `BND-PRT-10` | Marca en venta | `isForSale` es un indicador actual y auditado sin precio, oferta, comprador ni historia comercial. No cambia modalidad, disponibilidad, titularidad ni operaciones; una transferencia tampoco lo desmarca automaticamente. |
| `BND-IMP-01` | Importacion con filas invalidas | Preview valida el archivo completo. El usuario corrige o excluye filas y la confirmacion guarda todas las seleccionadas o ninguna. Revalida dentro de la transaccion contra cambios posteriores; un preview obsoleto devuelve conflicto por fila y campo. |
| `BND-IMP-02` | Reintento o segundo CSV | Confirmacion usa hash de archivo, seleccion, batch e idempotencia. Es create-only: datos iguales existentes se informan sin cambiar; datos distintos chocan. Las unidades importadas quedan `SETUP`; CSV no crea titularidades, modalidades, grants ni historia. |

#### 7.9.4 Contratos, disponibilidad y reservas

| ID | Caso frontera | Decision aprobada para V1 |
| --- | --- | --- |
| `BND-AVL-01` | Estado textual frente a fechas ocupadas | La disponibilidad usa un reclamo efectivo. `DRAFT` y contrato `ANNULLED` no reclaman; contrato activado o terminado reclama su intervalo efectivo. Reserva `CONFIRMED`/`CHECKED_IN` reclama el plan, `CHECKED_OUT` su prefijo y `CANCELLED`/`NO_SHOW` nada. Bloqueo confirmado reclama el plan o prefijo si termino antes; borrador o cancelado antes de iniciar no reclama. |
| `BND-AVL-02` | Carrera entre contrato, reserva, bloqueo, modalidad o archivo | Todas esas mutaciones bloquean primero la misma `Unit` y usan el mismo predicado de superposicion. Gana una sola operacion; las demas reciben `409 AVAILABILITY_CONFLICT` sin cargos ni outbox parciales. |
| `BND-CTR-01` | Contrato abierto o activado por error | V1 exige inicio y fin inclusivo finitos. Estados: `DRAFT`, `ACTIVE`, `FINISHED`, `RESCINDED`, `ANNULLED`; anular solo corrige una activacion sin ocupacion ni efectos confirmados. Fases proximo, vigente y vencido son derivadas. |
| `BND-CTR-02` | Varios responsables y un solo cargo | Cada vigencia tiene exactamente una `billingParty` elegida entre responsables. El cargo y saldo a favor pertenecen a esa cuenta; quien entrega el dinero puede registrarse aparte. Cambiar deudor es prospectivo en un inicio de periodo y no edita cargos emitidos. |
| `BND-CTR-03` | Meses con dia 29, 30 o 31 | Periodos mensuales se calculan siempre desde el ancla original con aritmetica civil y regla de fin de mes, nunca desde la fecha ajustada anterior. Son `[inicio, siguiente inicio)` y `recognitionDate` es el inicio. |
| `BND-CTR-04` | Cambio de canon a mitad de periodo | El cronograma cubre cada inicio cobrable exactamente una vez y solo cambia en un inicio de periodo. Un importe cero declara concesion y no genera cargo cero. Cambios sobre periodos emitidos usan ajustes enlazados, sin prorrateo automatico. |
| `BND-CTR-05` | Rescision a mitad de periodo | `effectiveEndDate` detiene periodos cuyo inicio sea posterior. Si el periodo ya inicio se conserva el canon completo y cualquier reduccion es un credito explicito. Renovar crea contrato enlazado y no edita el anterior. |
| `BND-MOR-01` | Worker omitido o regla de mora cambiada | El cierre exige cargo, concesion cero o excepcion auditada para cada ocurrencia. El cargo congela regla de mora; el recargo unico se evalua despues de vencimiento y gracia sobre saldo del cargo original, con clave natural estable. Una tasa usa partes por millon y redondea una sola vez al guarani, mitad hacia arriba. |
| `BND-RSV-01` | Transicion imposible | Solo se permite `DRAFT -> CONFIRMED -> CHECKED_IN -> CHECKED_OUT`; desde `CONFIRMED` tambien `CANCELLED` o `NO_SHOW`. No-show exige que llegue check-in sin ingreso, libera todo el reclamo y ejecuta la misma conciliacion financiera que una cancelacion, usando penalidad opcional reconocida en `noShowDate`. Despues de check-in se usa salida anticipada. |
| `BND-RSV-02` | Total acordado distinto del calculado | Noches, tarifa, extras y descuentos producen total calculado. Confirmar congela lineas y `agreedTotal`; una diferencia exige motivo. Deposito queda fuera. Se emite un cargo unico por total positivo con reconocimiento en check-in. |
| `BND-RSV-03` | Cancelacion con pagos y deposito | Cancelar antes del ingreso es una conciliacion atomica: libera fechas, corrige cargo no ganado, revierte aplicaciones, restaura deposito aplicado, crea penalidad positiva solo si corresponde con `recognitionDate = cancellationDate`, aplica retencion y registra reembolsos solo cuando salen fondos reales. |
| `BND-RSV-04` | Salida anticipada | Guarda fecha efectiva, conserva el prefijo ocupado y libera el sufijo. No reduce automaticamente el cargo; un credito es un hecho financiero separado. |
| `BND-RSV-05` | Editar reserva confirmada | Unidad, fechas y precio no se sobrescriben. Antes de check-in una reprogramacion crea reemplazo enlazado y concilia efectos. Despues solo se extiende checkout validando el sufijo; el cargo adicional usa como `recognitionDate` la primera noche agregada, normalmente el checkout anterior. Acortar usa salida anticipada. |
| `BND-RSV-06` | Bloqueo indefinido o corregido | Un bloqueo tiene `DRAFT`, `CONFIRMED`, `CANCELLED`, motivo e intervalo finito. Cancelar antes de iniciar libera todo; terminar iniciado conserva prefijo y libera sufijo. No crea huespedes, cargos ni ingreso. |
| `BND-AVL-03` | Porcentaje de ocupacion con bloqueos | Fechas archivadas no son capacidad. `sellable = active - blocked`, `occupied` cubre contratos y reservas, `available = sellable - occupied` y ocupacion es `occupied / sellable`; si el denominador es cero se informa N/A, no cero. |

#### 7.9.5 Finanzas, periodos y liquidaciones

| ID | Caso frontera | Decision aprobada para V1 |
| --- | --- | --- |
| `BND-FIN-01` | Cero, negativos y doble signo | Hechos fuente usan magnitud mayor que cero y tipo debito, credito, entrada o salida. Cargos, pagos, aplicaciones, reversiones, reembolsos, depositos y desembolsos no aceptan cero ni negativos; saldos y netos derivados si. |
| `BND-FIN-02` | Pago confirmado equivocado o dinero devuelto | Un draft es mutable. Confirmar fija importe y `receivedDate`, asigna recibo y puede aplicar atomicamente. Si nunca hubo recepcion se corrige tras revertir aplicaciones y sin reembolsos; si el dinero entro y salio se conserva el pago y se usa reembolso. |
| `BND-FIN-03` | Reversion parcial y reporte historico | La aplicacion original sigue confirmada. Reversiones parciales suman hasta su importe y se informan en `reversedDate`; el corte anterior conserva la aplicacion original. Una nueva aplicacion solo usa fondos liberados desde esa reversion. |
| `BND-FIN-04` | Dos usos concurrentes del mismo saldo | Aplicar, revertir, reembolsar o mover deposito bloquea periodo, fuentes y destinos en orden estable y recalcula dentro del lock. Nunca recorta automaticamente el pedido; si ya no cabe, toda la operacion devuelve `409`. |
| `BND-FIN-05` | Fecha elegida para atribuir cobro | Aplicacion junto al pago usa `appliedDate = receivedDate`. Una aplicacion o reversion posterior usa la `businessDate` de confirmacion y el cliente no la retrofecha. Cada fecha debe pertenecer a periodo abierto. |
| `BND-FIN-06` | Reembolso de fondos aplicados o internos | Solo un pago externo confirmado admite reembolso y solo hasta su saldo disponible. Primero se revierten aplicaciones necesarias. Una fuente de deposito no se reembolsa; se revierte su aplicacion y se devuelve el deposito. Corregir reembolso crea entrada enlazada. |
| `BND-DEP-01` | Deposito usado a medias | Aplicar deposito crea atomicamente movimiento decreciente, fuente interna consumida al 100 % y aplicacion al cargo del mismo acuerdo, unidad, cuenta y tenant. Revertir restaura retenido y deuda sin caja. No se transfiere entre acuerdos en V1. |
| `BND-PER-01` | Movimiento compitiendo con cierre | Ambos bloquean el mismo periodo. O el movimiento confirma antes y se incluye, o el cierre gana y el movimiento falla. No se crea un mes abierto anterior a uno cerrado para eludir la barrera cronologica. |
| `BND-PER-02` | Cierre o reapertura fuera de orden | Solo se cierra un mes civil terminado y en orden desde el primer mes financiero; vacios se materializan. Se reabre en orden inverso. Cualquier desembolso de una liquidacion del mes impide reabrirlo. |
| `BND-PER-03` | Correccion de mes cerrado | Usa fecha de referencia original para origen y titularidad, pero `postingDate = businessDate` en el periodo abierto de confirmacion. No modifica reportes ni liquidaciones confirmadas del mes cerrado. |
| `BND-FIN-07` | Muchos pagos pequenos y copropiedad | El cargo congela participaciones y montos objetivo por propietario. Cada aplicacion consume capacidad pendiente de esas lineas; al pagar por completo, la suma por propietario coincide exactamente con el cargo, sin sesgo acumulado. La reversion deshace lineas almacenadas. |
| `BND-LIQ-01` | Una aplicacion con varios propietarios | La fuente reclamable es cada efecto de atribucion propietario-evento, no toda la aplicacion. Preview no reclama. Confirmar bloquea propietario-periodo, verifica version y huella y crea una sola revision vigente. |
| `BND-LIQ-02` | Reapertura y revisiones | Reabrir sin desembolsos marca revisiones como `SUPERSEDED` y libera solo sus reclamos activos; la siguiente confirmacion crea revision monotona. Las revisiones reemplazadas conservan lineas y documentos historicos. |
| `BND-LIQ-03` | Neto cero o negativo | Se puede confirmar cualquier neto. Solo un neto positivo se marca pagado una vez y por su importe exacto, creando un desembolso. Neto cero o negativo no crea caja; pagos parciales, cobro al propietario y arrastre automatico quedan fuera de V1. |
| `BND-LIQ-04` | Preview obsoleto o lineas omitidas | La confirmacion toma el conjunto completo y determinista de fuentes elegibles; no permite editar importes ni excluir lineas. Si cambia version del cierre o huella de fuentes devuelve `409 STALE_PREVIEW`. |
| `BND-REP-01` | Saldos historicos tras correcciones | Todo corte suma hechos con fecha efectiva hasta el corte, no estados vigentes. Pagos externos menos aplicaciones mas reversiones menos reembolsos explican saldo no aplicado; cargos y creditos menos aplicaciones mas reversiones explican deuda. |
| `BND-REP-02` | Matriz mensual que no cuadra por resta | Devengado usa mes de `recognitionDate`; aplicado y gasto pagado usan su propia fecha del mes. `Deuda al cierre` es stock de todos los cargos hasta el ultimo dia, por lo que no se exige `devengado - aplicado = deuda` del mes. |
| `BND-REP-03` | Correccion que desaparece de caja | Cada familia proyecta magnitud positiva con signo por direccion y fecha propia. Caja suma recepciones externas y depositos, menos reembolsos, gastos pagados, depositos devueltos y desembolsos, mas o menos correcciones enlazadas y devoluciones reales de proveedor. Aplicaciones internas no mueven caja. El detalle conserva original y correccion. |

#### 7.9.6 Gastos, mantenimiento y aprobaciones

| ID | Caso frontera | Decision aprobada para V1 |
| --- | --- | --- |
| `BND-EXP-01` | Que objeto se aprueba | La aprobacion pertenece a una revision inmutable de un `Expense`, no a toda la incidencia. La incidencia mantiene su ciclo operativo y deriva si tiene propuestas pendientes. |
| `BND-EXP-02` | Estado pagado que pierde aprobacion | `lifecycleStatus` es `PLANNED`, `INCURRED`, `PAID`, `VOIDED`; `VOIDED` solo termina un plan no incurrido. Aprobacion se deriva como `NOT_REQUIRED`, `PENDING`, `APPROVED`, `REJECTED`, `BYPASSED`. Pagar exige incurrido, fecha no anterior y aprobacion, exencion o emergencia valida. |
| `BND-EXP-03` | Herencia y umbral ambiguos | Cada nivel declara `INHERIT`, `NO_APPROVAL` o `REQUIRE_APPROVAL` y reemplaza la politica superior completa. Cada unidad evalua su importe materializado con comparacion `importe >= umbral`; luego se unen partes aprobadoras sin duplicarlas. |
| `BND-EXP-04` | Politica requerida sin aprobadores | Ausencia de politica es `NOT_REQUIRED`. Una politica requerida que resuelve cero propietarios, titularidad incompleta o ningun representante habilitado es error de configuracion y no se autoaprueba. La decision es una por parte propietaria. |
| `BND-EXP-05` | Cambio mientras se decide | La revision congela politicas, propietarios, importes, lineas, proveedor, categoria, alcance, imputacion, fecha efectiva y presupuestos. El primer rechazo la cierra; reenviar crea nueva revision sin reutilizar aceptaciones. |
| `BND-EXP-06` | Gasto real menor al aprobado | La propuesta aprobada no se edita. El real puede ser menor o igual por las mismas lineas y alcance; agregar linea, cambiar descripcion sustancial, proveedor, categoria, fecha, unidades o superar cualquier limite exige nueva revision. Evidencia de ejecucion no invalida. |
| `BND-EXP-07` | Emergencia como aprobacion general | `EmergencyOverride` autoriza una sola revision y congela lo que se habria aprobado. Exige permiso, motivo y evidencia. No omite periodos, tenant, saldos, titularidad ni inmutabilidad; aumento o cambio de alcance exige otro override. |
| `BND-EXP-08` | Imputacion incompleta o dependiente del presente | Gasto usa XOR unidad/ubicacion, lineas positivas y total derivado. Unidad implica 100 % a ella; ubicacion elige sin distribuir, distribucion completa o atribucion directa valida. La fecha propuesta se congela antes de aprobar y materializa unidades y propietarios historicos. |
| `BND-EXP-09` | Dos traslados parciales al inquilino | Un gasto incurrido tiene libro de recuperaciones. Emitir cargo y vinculo bajo lock no permite que transferencias activas superen el monto elegible. Emitir no compensa el gasto; solo el cobro aplicado recupera, usando la instantanea patrimonial del gasto. |
| `BND-EXP-10` | Correccion o atribucion tardia | Un gasto incurrido o pagado se corrige con efecto inverso; una devolucion real del proveedor es entrada enlazada, no edicion. Una atribucion despues del cierre usa titularidad de `allocationEffectiveDate` y se contabiliza como ajuste de propietario en el periodo abierto sin duplicar caja global. |

#### 7.9.7 Documentos, notificaciones, jobs y recuperacion

| ID | Caso frontera | Decision aprobada para V1 |
| --- | --- | --- |
| `BND-DOC-01` | Carga incompleta, reemplazada o maliciosa | Una `UploadIntent` del tenant usa clave staging impredecible y estados `PENDING`, `VERIFYING`, `AVAILABLE`, `REJECTED`, `EXPIRED`. Finalizar es idempotente, verifica bytes finales, tamano, MIME real, SHA-256 y malware antes de crear version inmutable. Solo `AVAILABLE` se referencia. |
| `BND-DOC-02` | Duplicado por checksum | SHA-256 se calcula sobre bytes almacenados; `ETag` y valor cliente no son autoridad. Coincidencia solo alerta dentro del tenant: no comparte objetos ni audiencia y nunca revela coincidencias cruzadas. |
| `BND-DOC-03` | Cambio de plantilla o datos antes del worker | Publicar vuelve inmutable la version. La solicitud congela plantilla, assets, renderer, datos, filtros, filas, totales, locale, zona y hash. Reintentar genera la misma version; reemitir crea otra enlazada y conserva la anterior. |
| `BND-DOC-04` | Audiencia historica y partes sin login | La audiencia por partes y fecha se materializa al crear. Equipo se autoriza dinamicamente por membresia y permiso; propietarios requieren grant y audiencia, o ser titulares de la liquidacion referenciada. Partes sin login no reciben URL anonima: solo un PDF generado expresamente habilitado puede enviarse como adjunto transaccional; identificaciones y adjuntos sensibles no se envian automaticamente. |
| `BND-DOC-05` | Revocacion despues de emitir URL | Cada descarga reautoriza y emite URL para un objeto/version, con expiracion maxima de cinco minutos y sin persistirla ni registrarla. Revocar o suspender evita nuevas URLs; la ya emitida es una excepcion acotada hasta vencer. |
| `BND-NTF-01` | Consentimiento cambiado o recordatorio obsoleto | Mensajes se clasifican como identidad, transaccionales u operativos; marketing no existe en V1. Identidad se autoriza por `User` y proposito de seguridad; negocio usa habilitacion por `Party`, destino, canal y proposito. Se revalida antes de enviar. Recordatorios tienen revision, relevancia y expiracion; si el origen cambia se cancelan. |
| `BND-NTF-02` | Plantilla editada, callback duplicado o fuera de orden | Identidad logica usa ocurrencia, destinatario, destino, canal y proposito, no etiqueta mutable. Payload y version se congelan. Eventos del proveedor son append-only e idempotentes; el estado de entrega se deriva por tabla y nunca retrocede solo por orden de llegada. |
| `BND-NTF-03` | Timeout ambiguo de Resend | Cada entrega se persiste antes de llamar y reutiliza payload y clave de idempotencia. Segun documentacion vigente, Resend conserva la clave 24 horas y responde `409` si cambia payload; los reintentos automaticos terminan dentro de esa ventana. Despues, un resultado ambiguo requiere revision manual, no reenvio automatico. |
| `BND-NTF-04` | Firma, replay y timeout del bridge | Resend se verifica sobre body crudo y headers firmados antes de parsear. El bridge WhatsApp usa HMAC-SHA256 sobre timestamp, event ID y body crudo, key ID y ventana maxima de cinco minutos. El identificador de entrega es clave idempotente: mismo payload devuelve el resultado estable y otro payload produce conflicto. Callbacks validos se guardan en inbox durable antes de `2xx`; replay no repite transicion. |
| `BND-JOB-01` | Worker cae o termina con lease vencido | Outbox es inmutable. Jobs se reclaman en transaccion corta con `SKIP LOCKED`, lease, token y contador; se ejecutan fuera y cada heartbeat o finalizacion exige el token vigente. Un worker antiguo queda cercado. Reejecucion crea generacion enlazada sin borrar intentos. |
| `BND-JOB-02` | Restaurar backup reenvia efectos externos | Una restauracion inicia sin egress y con nuevo `restoreEpoch`; outbox, jobs y entregas anteriores quedan `RESTORE_HOLD`. Jobs internos deterministas se liberan tras verificar idempotencia; mensajes y otros efectos externos requieren reconciliacion o liberacion auditada. |
| `BND-OPS-01` | Base y objetos restaurados en puntos distintos | V1 usa PITR de PostgreSQL con objetivo `RPO <= 15 min`, `RTO <= 8 h`, base diaria cifrada 30 dias y versionado o recuperacion equivalente de objetos. La prueba trimestral verifica version, tamano y hash de cada objeto referenciado; no regenera silenciosamente documentos perdidos. |
| `BND-OPS-02` | Caida de proveedor degrada toda la API | Readiness depende de PostgreSQL y dependencias locales criticas. Resend, Spaces o bridge se muestran degradados sin bloquear movimientos que no los necesitan. Alertas cubren antiguedad de cola, leases vencidos, dead letters, envios ambiguos, callbacks invalidos, uploads atascados y fallos de respaldo. |

## 8. Requisitos funcionales

### 8.1 Organizaciones y onboarding

- `ORG-01`: el superadministrador debe poder crear una organizacion y enviar invitacion a su primer administrador.
- `ORG-02`: una persona debe poder autorregistrarse, verificar su email y crear una organizacion activa.
- `ORG-03`: el sistema debe aplicar la suspension definida en `BND-IAM-02`, conservar todos los datos y revalidar trabajos retenidos al reactivar.
- `ORG-04`: cada organizacion debe configurar nombre legal y comercial, RUC opcional, direccion, contactos, logo, zona horaria y prefijo de recibos.
- `ORG-05`: la organizacion debe configurar dias de aviso, reglas de mora, categorias, tipos de unidad, medios de pago y politicas de aprobacion.
- `ORG-06`: el sistema debe incluir valores iniciales utiles sin impedir su edicion o desactivacion.
- `ORG-07`: la facturacion del SaaS debe permanecer fuera del flujo de negocio de V1.

### 8.2 Identidad, roles y permisos

- `IAM-01`: el acceso debe usar email verificado y contrasena.
- `IAM-02`: deben existir invitacion de un uso, aceptacion, recuperacion de contrasena y cierre revocable de sesiones activas.
- `IAM-03`: un usuario puede pertenecer a varias organizaciones y debe elegir un contexto activo versionado; una mutacion de una pestana obsoleta nunca se redirige al tenant nuevo.
- `IAM-04`: el administrador puede crear roles con permisos por accion segun `BND-IAM-07`, sin grants directos, denies ni comodines.
- `IAM-05`: el sistema debe ofrecer plantillas editables de administrador, operador, cobranzas y mantenimiento.
- `IAM-06`: el acceso de propietario exige grant explicito y debe estar limitado por sus titularidades e instantaneas atribuidas, separado de permisos internos.
- `IAM-07`: cambios de roles, permisos, miembros y acceso de propietario deben quedar auditados.
- `IAM-08`: los roles internos de V1 habilitan acciones sobre toda la organizacion; el alcance por ubicacion o unidad queda fuera de V1.

### 8.3 Partes

- `PTY-01`: una parte puede ser persona fisica o juridica.
- `PTY-02`: debe admitir nombre, documento o RUC, contactos, direccion, observaciones y archivos.
- `PTY-03`: una misma parte puede actuar en varios roles sin duplicar su identidad.
- `PTY-04`: documento/RUC normalizado y tipado debe ser unico por organizacion; email o telefono generan alerta blanda y exigen resolucion explicita. Fusionar partes referenciadas queda fuera de V1.
- `PTY-05`: una parte referenciada historicamente se archiva; no se elimina fisicamente.

### 8.4 Ubicaciones y unidades

- `PRT-01`: una organizacion puede crear cualquier cantidad de ubicaciones dentro del limite operativo contratado externamente.
- `PRT-02`: una ubicacion debe admitir nombre, codigo, direccion, descripcion, contactos, archivos y estado `ACTIVE` o `ARCHIVED`.
- `PRT-03`: una ubicacion puede contener una o muchas unidades.
- `PRT-04`: la unidad debe admitir codigo unico dentro de la ubicacion, nombre visible editable, tipo fisico, descripcion, archivos, estado administrativo `SETUP`, `ACTIVE` o `ARCHIVED`, `activatedDate` y `archivedDateExclusive`.
- `PRT-05`: si el usuario no asigna un nombre, el sistema debe sugerir `<prefijo-ubicacion>-<secuencia>`; si no existe prefijo, `Unidad <secuencia>`.
- `PRT-06`: el usuario puede editar el nombre sugerido sin alterar identificadores internos ni historia.
- `PRT-07`: los tipos fisicos deben ser catalogos configurables, por ejemplo casa, duplex, departamento, cabana y salon comercial.
- `PRT-08`: una unidad activa debe tener una sola modalidad continua por intervalos semiabiertos: tradicional, temporaria o comercial.
- `PRT-09`: la unidad puede marcarse en venta sin bloquear contratos o reservas.
- `PRT-10`: archivar una unidad exige no tener reclamos presentes o futuros, no cancela en cascada, impide operaciones nuevas y conserva liquidacion y correccion de historia.
- `PRT-11`: el sistema debe mostrar disponibilidad y ocupacion derivadas de contratos, reservas, bloqueos y estados administrativos.

### 8.5 Titularidad y copropiedad

- `OWN-01`: una unidad debe admitir una o varias partes propietarias con porcentajes.
- `OWN-02`: toda titularidad usa `[fromDate, toDateExclusive)` y puede quedar abierta al futuro.
- `OWN-03`: la suma vigente de una unidad `ACTIVE` debe ser exactamente `1.000.000` partes por millon en toda su vigencia.
- `OWN-04`: un cambio reemplaza atomicamente la composicion completa desde una fecha y conserva distribucion e instantaneas historicas anteriores.
- `OWN-05`: el administrador debe poder designar usuarios de portal vinculados a cada parte propietaria.
- `OWN-06`: los reportes del propietario deben respetar su porcentaje historico para cada periodo.

### 8.6 Contratos tradicionales y comerciales

- `CTR-01`: cada registro de contrato debe referenciar exactamente una unidad; una unidad puede conservar varios contratos historicos no superpuestos.
- `CTR-02`: una parte puede mantener contratos separados sobre varias unidades.
- `CTR-03`: el contrato debe admitir uno o varios inquilinos responsables, exactamente una `billingParty` vigente entre ellos y garantes opcionales.
- `CTR-04`: debe contener modalidad, inicio y fin inclusivo finitos, dia de vencimiento, cronograma de importes, deposito, regla de mora y documentos.
- `CTR-05`: los estados persistidos deben ser `DRAFT`, `ACTIVE`, `FINISHED`, `RESCINDED` y `ANNULLED`; anular solo corrige activacion sin ocupacion ni efectos, y las fases temporales son derivadas.
- `CTR-06`: activar un contrato debe validar unidad, titularidad, partes, cronograma y ausencia de conflictos.
- `CTR-07`: el cronograma debe permitir cambios de canon pactados con fecha futura.
- `CTR-08`: cambiar el cronograma no debe modificar cargos ya emitidos; una correccion retroactiva requiere ajuste auditable.
- `CTR-09`: el worker debe generar los cargos mensuales de forma idempotente.
- `CTR-10`: finalizar o rescindir detiene periodos cuyo inicio sea posterior al fin efectivo, conserva el periodo ya iniciado completo y mantiene deuda, pagos, documentos y deposito.
- `CTR-11`: una renovacion debe crear un nuevo periodo contractual o contrato enlazado, sin sobrescribir el anterior.
- `CTR-12`: el sistema debe avisar proximos vencimientos y contratos por finalizar segun configuracion.
- `CTR-13`: contratos tradicionales y comerciales no pueden superponerse entre si para una unidad.
- `CTR-14`: un contrato tradicional/comercial no puede superponerse con una reserva confirmada o bloqueo; la marca en venta no participa en esta validacion.

### 8.7 Mora

- `MOR-01`: la organizacion define una regla por defecto y cada contrato puede reemplazarla.
- `MOR-02`: el modo manual debe calcular dias de atraso y permitir agregar un cargo de mora con detalle.
- `MOR-03`: el modo automatico debe admitir dias de gracia y un recargo unico fijo o porcentual sobre saldo del cargo original al primer dia elegible.
- `MOR-04`: el recargo automatico debe ser idempotente por cargo original y version congelada de regla; el cierre detecta ocurrencias omitidas.
- `MOR-05`: el usuario con permiso debe poder anular economicamente un recargo mediante credito enlazado y motivo, sin ocultar el cargo original.

### 8.8 Reservas temporarias

- `RSV-01`: el calendario debe mostrar reservas y bloqueos por unidad y rango de fechas.
- `RSV-02`: una reserva debe contener huespedes, check-in, check-out, tarifa, extras, descuentos, deposito, notas y origen manual.
- `RSV-03`: el precio debe calcularse a partir de noches y tarifa base, permitiendo un total acordado editable antes de confirmar.
- `RSV-04`: los estados y transiciones deben seguir `BND-RSV-01`; despues de check-in no existe cancelacion, sino salida anticipada.
- `RSV-05`: confirmar debe volver a validar disponibilidad dentro de una transaccion.
- `RSV-06`: un bloqueo debe reservar fechas sin crear huesped ni ingreso.
- `RSV-07`: confirmar una reserva debe generar sus cargos sin duplicados.
- `RSV-08`: cancelar antes del ingreso debe ejecutar atomicamente la conciliacion de `BND-RSV-03`; una salida anticipada conserva el prefijo ocupado y no reduce automaticamente el cargo.
- `RSV-09`: V1 no debe importar ni exportar disponibilidad a plataformas externas.

### 8.9 Cargos, pagos y recibos

- `FIN-01`: un cargo debe identificar parte deudora, unidad, concepto, `recognitionDate`, periodo de servicio opcional, emision, vencimiento, importe y origen.
- `FIN-01A`: el ciclo persistido de un cargo debe ser borrador o emitido; un borrador puede descartarse. Abierto, parcial, pagado, vencido y corregido se calculan desde saldo, fechas y efectos correctivos enlazados.
- `FIN-02`: los conceptos pueden ser alquiler, mora, servicio, gasto trasladado, reserva u otra categoria configurable.
- `FIN-03`: un pago externo manual debe registrar parte, `receivedDate`, medio, importe, referencia, observacion y comprobante opcional.
- `FIN-04`: los medios iniciales deben incluir efectivo, transferencia y otro; la organizacion puede ampliarlos.
- `FIN-05`: un pago puede aplicarse total o parcialmente a uno o varios cargos de la misma organizacion y parte deudora.
- `FIN-06`: la suma de aplicaciones activas y reembolsos confirmados no puede superar el importe del pago; una aplicacion tampoco puede superar el saldo del cargo.
- `FIN-07`: el importe del pago menos aplicaciones activas y reembolsos confirmados permanece como saldo a favor no aplicado.
- `FIN-08`: confirmar un pago externo debe generar un numero secuencial unico y un recibo interno no fiscal.
- `FIN-09`: corregir un pago confirmado sin recepcion real exige revertir aplicaciones y crear un efecto enlazado; si el dinero fue recibido y luego devuelto, debe usarse un reembolso. Ambos conservan recibo, motivo e historia.
- `FIN-10`: el sistema debe admitir numero, timbrado, fecha y archivo de una factura externa sin emitirla ni validarla fiscalmente.
- `FIN-11`: los periodos financieros pueden cerrarse; reabrir exige permiso especial, motivo y auditoria.
- `FIN-12`: un pago externo debe pasar de borrador a confirmado o anulado; su importe y fecha de recepcion quedan fijos al confirmar. Una fuente `DEPOSIT_APPLICATION` se crea confirmada y marcada como no monetaria.
- `FIN-13`: una aplicacion debe guardar `appliedDate`, que no puede ser anterior a la fecha de disponibilidad de su fuente y determina su periodo de atribucion a unidad/propietario.
- `FIN-14`: si el pago se aplica al confirmarlo, `appliedDate` coincide con `receivedDate`; una aplicacion posterior pertenece al periodo en que se confirma.
- `FIN-15`: revertir una aplicacion crea un evento inverso de magnitud positiva y `reversedDate`; no elimina ni retrofecha la aplicacion original. Si ya fue liquidada, la reversion se incluye como ajuste en la liquidacion elegible del periodo de `reversedDate`.
- `FIN-16`: la entrada de caja se informa por `receivedDate`, mientras el cobro atribuible se informa por `appliedDate`; ambas metricas deben permanecer separadas.
- `FIN-17`: una aplicacion incluida en una liquidacion pagada solo se corrige mediante una reversion/ajuste fechado en un periodo abierto; la liquidacion pagada permanece intacta.
- `FIN-18`: el primer movimiento de un mes crea automaticamente su periodo abierto si todavia no existe y si no viola la barrera cronologica de `BND-PER-01`.
- `FIN-19`: un reembolso debe referenciar un pago externo confirmado y registrar `refundedDate`, importe, medio, referencia, motivo y comprobante opcional.
- `FIN-20`: antes de reembolsar fondos aplicados deben revertirse las aplicaciones necesarias en un periodo abierto; el reembolso solo usa saldo a favor disponible.
- `FIN-21`: el reembolso reduce caja, no ingreso devengado ni gasto, y nunca retrocede la fecha de recepcion original.
- `FIN-22`: si la recepcion original pertenece a un periodo cerrado, la reversion y el reembolso se registran en el periodo abierto de sus fechas efectivas.
- `FIN-23`: una cancelacion con retencion debe emitir o conservar el cargo de penalidad, aplicar fondos a ese cargo y reembolsar solamente el remanente disponible.

### 8.10 Depositos de garantia

- `DEP-01`: un deposito debe vincularse a un contrato o reserva y registrarse separado de cargos e ingreso.
- `DEP-02`: debe mostrar importe acordado, recibido, saldo retenido, aplicaciones y devoluciones.
- `DEP-03`: el saldo se calcula desde movimientos confirmados de recepcion, aplicacion, devolucion y correccion; nunca puede ser negativo.
- `DEP-04`: recibir un deposito aumenta fondos retenidos y entrada de caja, pero no ingreso ni monto liquidable.
- `DEP-05`: aplicar un deposito exige un cargo emitido. El sistema crea una fuente interna `DEPOSIT_APPLICATION` y una aplicacion al cargo, reduce el fondo retenido y no registra una segunda entrada de caja.
- `DEP-06`: la aplicacion del deposito se considera cobro atribuible y puede entrar en la liquidacion del propietario por su `appliedDate`.
- `DEP-07`: una retencion por dano, deuda o cancelacion debe representarse con un cargo justificado y la aplicacion del deposito a ese cargo.
- `DEP-08`: una devolucion reduce fondos retenidos y se muestra como salida de caja no operativa, no como gasto.
- `DEP-09`: anular o corregir un movimiento crea trazabilidad y no cambia silenciosamente movimientos anteriores.

### 8.11 Gastos

- `EXP-01`: un gasto debe pertenecer inicialmente a una unidad o una ubicacion, nunca a ambas.
- `EXP-02`: debe admitir categoria configurable, proveedor opcional, fecha, descripcion general, estado, comprobantes y fecha de pago.
- `EXP-03`: debe admitir una o varias lineas de detalle con descripcion e importe.
- `EXP-04`: la suma de lineas debe coincidir exactamente con el total del gasto.
- `EXP-05`: el ciclo financiero del gasto es `PLANNED`, `INCURRED`, `PAID` o `VOIDED`; solo un plan no incurrido pasa a `VOIDED`. El estado de aprobacion se deriva por separado segun `BND-EXP-02`.
- `EXP-05A`: al pasar a incurrido debe fijar `incurredDate`; al pasar a pagado debe fijar `paidDate` y conservar `incurredDate` para el criterio devengado.
- `EXP-06`: V1 registra un unico total pagado por gasto; cuotas a proveedores y cuentas por pagar avanzadas quedan fuera.
- `EXP-07`: un gasto de ubicacion queda sin distribuir por defecto.
- `EXP-08`: el usuario puede imputarlo a una unidad, a unidades seleccionadas por partes iguales o a todas las unidades activas en `allocationEffectiveDate` por partes iguales.
- `EXP-09`: un gasto sin distribuir aparece en reportes de ubicacion y organizacion bajo "sin imputar", pero no se atribuye a una unidad o propietario.
- `EXP-10`: si todas las unidades afectadas tienen el mismo propietario, el usuario puede atribuir el gasto directamente a ese propietario sin distribuirlo por unidad.
- `EXP-11`: con propietarios distintos, toda atribucion a liquidaciones debe ser explicita o derivarse de unidades imputadas y sus participaciones.
- `EXP-12`: un gasto atribuible al inquilino puede generar un cargo vinculado por el total o por una parte.
- `EXP-13`: el gasto y el cargo trasladado deben conservar referencias reciprocas para evitar doble recuperacion.
- `EXP-14`: confirmar una imputacion debe guardar lineas concretas de unidad, propietario, porcentaje e importe; cambios posteriores de cartera no la recalculan.
- `EXP-15`: modificar importe, lineas, alcance, imputacion o presupuesto despues de solicitar aprobacion invalida las aprobaciones anteriores.

### 8.12 Incidencias y aprobaciones

- `MNT-01`: una incidencia debe incluir ubicacion o unidad, titulo, detalle, prioridad, reportante, responsable, fechas y adjuntos.
- `MNT-02`: los estados operativos deben ser abierta, en evaluacion, pendiente de aprobacion, aprobada, en curso, resuelta, cerrada y cancelada; pendiente/aprobada se derivan de la revision de gasto vigente y no autorizan otros gastos de la incidencia.
- `MNT-03`: una incidencia puede agrupar estimaciones, aprobaciones y gastos reales.
- `MNT-04`: organizacion, ubicaciones y unidades pueden definir politica completa con umbral inclusivo y partes propietarias requeridas; prevalece unidad, luego ubicacion y finalmente organizacion segun `BND-EXP-03`.
- `MNT-05`: una aprobacion pertenece a una revision de gasto, se completa cuando todas las partes requeridas aceptan y el primer rechazo la cierra; reenviar crea revision nueva.
- `MNT-06`: una emergencia puede omitir aprobacion previa solamente con permiso, motivo y evidencia.
- `MNT-07`: propietarios y equipo deben recibir avisos de solicitud, decision y cambio relevante de estado.
- `MNT-08`: un gasto sin imputacion de unidad usa la politica de ubicacion; un gasto imputado a unidades combina el conjunto de aprobadores requeridos de esas unidades sin duplicarlos.
- `MNT-09`: la solicitud de aprobacion congela una version de monto, lineas, alcance, imputacion y documentos de presupuesto.
- `MNT-10`: un gasto real menor o igual al monto aprobado puede continuar; cualquier aumento o cambio de alcance exige una nueva aprobacion, salvo emergencia justificada.

### 8.13 Liquidaciones a propietarios

- `LIQ-01`: una liquidacion debe pertenecer a un propietario y a un periodo financiero mensual cerrado.
- `LIQ-02`: se calcula con atribucion de caja: aplicaciones confirmadas por `appliedDate` menos gastos pagados por `paidDate`, ambos atribuibles al propietario.
- `LIQ-03`: la participacion de los cobros procede de la instantanea del cargo; la de gastos procede de su imputacion e instantanea.
- `LIQ-04`: cobros no aplicados, depositos retenidos y gastos sin atribuir se muestran como informativos y no integran el neto liquidable.
- `LIQ-05`: V1 no descuenta comision automatica de administradora.
- `LIQ-06`: un honorario excepcional puede cargarse manualmente como gasto detallado y auditable.
- `LIQ-07`: la vista previa debe permitir detectar movimientos sin imputar antes de confirmar.
- `LIQ-08`: confirmar crea una instantanea inmutable con sus lineas y totales.
- `LIQ-09`: una liquidacion de neto positivo puede marcarse pagada una sola vez por su importe exacto, con fecha, medio, referencia y comprobante; crea una salida `OwnerDisbursement`, no un gasto. Neto cero o negativo no se marca pagado.
- `LIQ-10`: reabrir el periodo sin desembolsos exige permiso, motivo y auditoria, y marca la revision como `SUPERSEDED` sin sobrescribirla. Una liquidacion con desembolso no se anula ni reabre; se corrige por ajustes posteriores.
- `LIQ-11`: el propietario puede consultar y descargar solamente sus liquidaciones.
- `LIQ-12`: una fuente financiera atribuida no puede formar parte de dos liquidaciones activas del mismo propietario.
- `LIQ-13`: debe existir una sola revision vigente por propietario y periodo; una reemision conserva y marca como reemplazada la revision anterior.
- `LIQ-14`: una liquidacion pagada no se recalcula; toda diferencia posterior se incluye como ajuste enlazado en un periodo abierto.

### 8.14 Documentos y archivos

- `DOC-01`: se deben generar PDF de contratos, reservas, recibos, liquidaciones y reportes desde plantillas versionadas.
- `DOC-02`: una plantilla puede configurar identidad visual, encabezado, pie, clausulas y variables autorizadas.
- `DOC-03`: un documento generado debe conservar los datos resueltos y la version de plantilla usada.
- `DOC-04`: deben poder adjuntarse contratos firmados fuera del sistema, identificaciones, fotos, comprobantes y facturas externas.
- `DOC-05`: todos los objetos deben almacenarse de forma privada en DigitalOcean Spaces.
- `DOC-06`: la descarga debe usar autorizacion previa y URL firmada de corta duracion.
- `DOC-07`: el metadato debe incluir organizacion, agregado al que se adjunta, nombre original, tipo, tamano, checksum y autor.
- `DOC-08`: un archivo referenciado se archiva o versiona; no se reemplaza silenciosamente.
- `DOC-09`: cada documento debe declarar audiencia: solo equipo, propietarios afectados o partes seleccionadas.
- `DOC-10`: para portal, el backend debe validar grant vigente y ademas audiencia materializada con interseccion historica, o que el documento pertenezca a una liquidacion de esa parte. Equipo interno se autoriza por membresia y permiso. La URL firmada dura hasta cinco minutos.

### 8.15 Notificaciones

- `NTF-01`: email se envia mediante Resend.
- `NTF-02`: WhatsApp se entrega a un webhook HTTPS de despliegue mediante `POST` firmado; el bridge externo traduce el mensaje al proveedor elegido.
- `NTF-03`: las plantillas deben ser configurables por organizacion y canal, con variables controladas.
- `NTF-04`: los eventos iniciales incluyen vencimiento proximo, mora, contrato por finalizar, reserva confirmada, recordatorio de estadia, aprobacion de gasto, incidencia y liquidacion disponible.
- `NTF-05`: cada envio debe registrar destinatario, consentimiento o habilitacion del canal, plantilla, estado, intentos, respuesta del proveedor y fecha.
- `NTF-06`: despacho y entrega se modelan por separado; los eventos de proveedor son append-only y el estado derivado no retrocede por callbacks duplicados o fuera de orden.
- `NTF-07`: un fallo debe reintentarse con espera creciente y limite configurable; despues debe quedar visible para reenvio manual.
- `NTF-08`: fallar un mensaje no debe revertir un pago, reserva, gasto o liquidacion ya confirmados.
- `NTF-09`: el webhook debe recibir identificador idempotente, destinatario, plantilla, variables y texto renderizado, devolver resultado estable para reintentos identicos y aceptar callbacks firmados de estado asociados al mismo identificador.
- `NTF-10`: si no hay webhook configurado, el canal WhatsApp se muestra deshabilitado y no se encolan mensajes que aparenten haber sido enviados.
- `NTF-11`: V1 debe probar el contrato del webhook con un receptor HTTP controlado; la seleccion y operacion del bridge de produccion no forman parte del nucleo.

### 8.16 Importacion

- `IMP-01`: el usuario puede cargar ubicaciones, unidades y partes mediante formularios.
- `IMP-02`: debe existir una plantilla CSV separada para ubicaciones, unidades y partes.
- `IMP-03`: la importacion debe validar estructura, datos, duplicados y referencias antes de confirmar.
- `IMP-04`: la vista previa debe indicar filas validas y errores con numero de fila y campo, y conservar hash, seleccion y version para detectar obsolescencia.
- `IMP-05`: el usuario debe corregir o excluir filas invalidas; confirmar vuelve a validar y guarda todas las filas seleccionadas o ninguna.
- `IMP-06`: los contratos y movimientos iniciales se cargan manualmente en V1.

### 8.17 Auditoria

- `AUD-01`: deben auditarse accesos administrativos, cambios de permisos, titularidades, modalidades, contratos, reservas, movimientos, periodos, aprobaciones y documentos sensibles.
- `AUD-02`: el evento debe declarar alcance de plataforma u organizacion, actor tipado, accion, entidad, instante, correlacion y cambios permitidos antes/despues; `organizationId` es obligatorio solo para alcance organizacional.
- `AUD-03`: no deben guardarse contrasenas, tokens, contenido completo de archivos ni secretos en auditoria.
- `AUD-04`: los eventos de auditoria no pueden editarse desde la aplicacion.
- `AUD-05`: usuarios autorizados deben poder buscar auditoria por actor, entidad, accion y fechas.

## 9. Reportes y definiciones financieras

### 9.1 Dimensiones y filtros

Todos los reportes deben permitir, cuando corresponda, filtrar por:

- Rango de fechas o mes.
- Propietario.
- Ubicacion.
- Unidad.
- Tipo fisico.
- Modalidad.
- Ocupacion o disponibilidad.
- Parte inquilina o huesped.
- Categoria de cargo o gasto.
- Estado de contrato, reserva, cargo, pago, gasto o liquidacion.
- Criterio devengado o caja.

### 9.2 Definiciones

| Indicador | Calculo de V1 |
| --- | --- |
| Ingreso devengado | Proyeccion con signo de cargos emitidos por `recognitionDate` y creditos o ajustes enlazados por `postingDate`. El importe no se prorratea por interseccion. |
| Entrada de caja | Proyeccion con signo de pagos externos por `receivedDate`, recepciones de deposito y correcciones enlazadas por su propia fecha; no implica atribucion a unidad o propietario. |
| Cobrado aplicado | Proyeccion con signo de aplicaciones por `appliedDate`, incluidas fuentes de deposito, y reversiones por `reversedDate`. |
| Cobro no aplicado | Al corte, pagos externos y sus correcciones menos aplicaciones externas, mas reversiones y menos reembolsos, incluyendo correcciones de reembolso; no se atribuye a unidad o propietario. |
| Saldo pendiente | Al corte, debitos de cargos menos creditos, aplicaciones y sus efectos inversos, todos por su fecha correspondiente. |
| Gasto devengado | Proyeccion con signo de gastos incurridos por `incurredDate` y sus correcciones por `postingDate`, atribuidos o sin atribuir segun el reporte. |
| Gasto de caja | Proyeccion con signo de pagos de gastos por `paidDate`, correcciones y devoluciones reales de proveedor por su fecha propia. |
| Fondos retenidos | Al corte, proyeccion con signo de recepciones, aplicaciones, restauraciones, devoluciones y correcciones de deposito. |
| Resultado devengado | Ingreso devengado menos gasto devengado, sin incluir depositos. |
| Resultado cobrado atribuible | Cobrado aplicado menos gasto de caja atribuible; no es igual a entrada bancaria cuando existen cobros sin aplicar o depositos. |
| Reembolsos externos | Proyeccion con signo de devoluciones por `refundedDate` y sus correcciones; reducen caja, pero no se registran como gasto. |
| Flujo de caja registrado | Suma de todos los efectos de caja con su direccion y fecha: recepciones, salidas, devoluciones de proveedor y correcciones enlazadas. Las aplicaciones internas no vuelven a mover caja. |
| Ocupacion | Noches o dias ocupables cubiertos por contrato/reserva frente al total disponible del rango. |

Una aplicacion creada despues del pago no mueve la entrada de caja original. Se atribuye a unidad y propietario en `appliedDate`. Por eso un reporte puede mostrar entrada de caja en agosto y cobro aplicado en septiembre sin contar dos veces el dinero.

Los importes de cada hecho permanecen positivos. Las tablas de detalle muestran direccion, original y correccion; los totales aplican la proyeccion con signo materializada para evitar doble negacion o desaparicion de una correccion.

Un cargo cuyo servicio va del 20 de agosto al 19 de septiembre se reconoce completo en agosto si `recognitionDate` es 20 de agosto. El reporte de ocupacion si distribuye los dias por interseccion, pero el financiero no prorratea ese cargo.

### 9.3 Reportes obligatorios

| Reporte | Regla temporal | Filtros minimos | Salida y agrupacion minima |
| --- | --- | --- | --- |
| Resumen ejecutivo | Rango; muestra devengado, entrada, aplicacion y caja con sus fechas propias. | Propietario, ubicacion, unidad. | Sin filtro patrimonial muestra cargos, entrada, reembolsos, aplicado, deuda, gastos, depositos y flujo; con filtro patrimonial sustituye entrada/flujo global por importes aplicados y atribuibles. |
| Matriz mensual por unidad | Mes de `recognitionDate` para devengado; `appliedDate` y `paidDate` para atribucion de caja. | Propietario, ubicacion, modalidad, estado operativo. | Una fila por unidad cuya vigencia activa intersecta el mes con ocupacion, devengado, cobrado aplicado, deuda total al cierre, gasto devengado y pagado; entradas no aplicadas aparecen en un resumen separado. |
| Ingresos y egresos | Rango y criterio elegido; siempre identifica la fecha usada. | Propietario, ubicacion, unidad, categoria. | A nivel organizacion incluye entradas/reembolsos; con dimension patrimonial usa aplicaciones y gastos atribuibles, agrupables por dia, mes, categoria y alcance. |
| Estado de cuenta de parte | Cargos por periodo y aplicaciones por `appliedDate`, con fecha de corte inclusiva. | Parte, unidad, contrato o reserva. | Cronologia de cargos, aplicaciones, reversiones, saldo a favor y deuda acumulada. |
| Morosidad | Saldo existente al cierre de la fecha de corte. | Propietario, ubicacion, unidad, parte. | Cargo, vencimiento, saldo y tramos 1-30, 31-60, 61-90 y mas de 90 dias. |
| Ocupacion y vacancia | Interseccion de contrato/reserva/bloqueo con el rango. | Propietario, ubicacion, unidad, modalidad. | Dias o noches disponibles, ocupados, bloqueados y porcentaje por unidad y ubicacion. |
| Reservas temporarias | Estadias por check-in/check-out; finanzas por fecha de cargo, aplicacion o pago. | Ubicacion, unidad, huesped, estado. | Estadias, noches, tarifa, cargos, cobrado aplicado, saldo, cancelaciones y ocupacion. |
| Contratos | Estado a una fecha de corte o eventos dentro de un rango. | Propietario, ubicacion, unidad, modalidad, estado. | Partes, vigencia, canon aplicable, proximo vencimiento, deuda y deposito. |
| Gastos | `incurredDate` para devengado o `paidDate` para caja. | Propietario, ubicacion, unidad, categoria, proveedor, aprobacion. | Lineas, total, estado, imputacion, atribucion, cargo trasladado y agrupaciones por categoria/alcance. |
| Depositos | Movimientos por su fecha efectiva y saldo a fecha de corte. | Ubicacion, unidad, parte, contrato/reserva, estado. | Acordado, recibido, retenido, aplicado, devuelto y referencias de cargos. |
| Liquidaciones | Periodo financiero mensual. | Propietario, estado, ubicacion de origen. | Lineas fuente, cobrado aplicado, gastos pagados, ajustes, informativos, neto y revision. |
| Sin aplicar o imputar | Existencia a fecha de corte. | Tipo de movimiento, propietario, ubicacion, unidad, antiguedad. | Cobros no aplicados, gastos sin imputar/atribuir y motivo de exclusion de liquidaciones. |
| Auditoria | Fecha/hora del evento dentro del rango. | Actor, accion, entidad. | Cronologia, correlacion y cambios autorizados, respetando ocultamiento de secretos. |

La fecha final de un filtro civil es inclusiva en la zona horaria de la organizacion. Cada reporte debe mostrar la regla temporal aplicada y la fecha de corte para evitar interpretar una aplicacion como si fuera la recepcion original del pago.

### 9.4 Reglas de presentacion

- Una unidad cuya vigencia activa intersecta el periodo debe aparecer en la matriz aunque este desocupada y tenga ingresos cero.
- Un gasto de ubicacion sin distribuir debe aparecer una sola vez y nunca duplicarse al agrupar unidades.
- El reporte de propietario incluye solo movimientos atribuidos a ese propietario y su participacion.
- Entrada de caja, reembolsos y flujo bancario se muestran solamente sin filtros de propietario, ubicacion o unidad, porque no tienen atribucion patrimonial antes de una aplicacion.
- Al aplicar un filtro patrimonial, el sistema muestra cobrado aplicado, gastos atribuibles y resultado atribuible; no reparte pagos no aplicados de forma artificial.
- Los totales PYG se presentan sin decimales y con separador local.
- La pantalla y el PDF deben usar el mismo conjunto de datos, filtros y reglas de calculo.
- Los PDF grandes se generan de forma asincrona y quedan disponibles mediante enlace autorizado.

### 9.5 Caso de referencia aprobado

Para agosto, una consulta debe poder mostrar:

| Unidad | Devengado | Cobrado | Pendiente | Gastos | Situacion |
| --- | ---: | ---: | ---: | ---: | --- |
| D1 | PYG 2.000.000 | PYG 2.000.000 | PYG 0 | PYG 70.000 | Ocupada; reparacion de plomeria y cambio de canilla detallados. |
| D2 | PYG 0 | PYG 0 | PYG 0 | PYG 500.000 | Desocupada; mantenimiento con una o varias lineas que suman PYG 500.000. |

El mismo motor debe consolidar el Edificio XX de la ubicacion NN, el Duplex XY de la ubicacion NM, ambos en conjunto o solamente la unidad XY1, siempre por el rango seleccionado.

## 10. Flujos principales

### 10.1 Alta y cartera

1. El usuario verifica su email o acepta una invitacion.
2. Crea o ingresa a su organizacion.
3. Completa configuracion basica y catalogos.
4. Carga manualmente o importa ubicaciones, unidades y partes.
5. Define modalidad, titularidad y acceso de propietarios.
6. El sistema valida porcentajes, codigos y duplicados antes de activar la cartera.

### 10.2 Contrato y cobro mensual

1. El operador crea un contrato en borrador para una unidad.
2. Agrega partes, fechas, cronograma, deposito y mora.
3. El sistema valida conflictos y activa el contrato.
4. El worker genera el cargo del periodo una sola vez.
5. El operador registra un pago manual y adjunta comprobante.
6. El pago se aplica a uno o varios cargos y se emite recibo interno.
7. Si queda saldo vencido, se calcula atraso y se ejecuta la regla manual o automatica.
8. Reportes y portal de propietario reflejan devengado, caja y deuda por separado.

### 10.3 Reserva temporaria

1. El operador consulta disponibilidad.
2. Crea una reserva en borrador y calcula noches, tarifa y extras.
3. Al confirmar, la API vuelve a comprobar superposiciones dentro de una transaccion.
4. Se ocupan las fechas y se generan cargos.
5. Se registran pagos, deposito, check-in y check-out.
6. Si se cancela, se liberan las fechas y se determina la penalidad o retencion manual.
7. Se revierten aplicaciones a cargos no ganados, se aplica el importe retenido al cargo de penalidad y se reembolsa solamente el saldo externo disponible.

### 10.4 Incidencia y gasto

1. El equipo registra una incidencia con evidencia.
2. Agrega estimacion o gasto y define alcance.
3. El sistema evalua monto y aprobadores configurados.
4. Los propietarios requeridos aprueban o rechazan.
5. El responsable ejecuta el trabajo y registra detalles/comprobantes.
6. El gasto se paga y se imputa a ubicacion, unidades o propietarios.
7. Si corresponde al inquilino, se genera un cargo vinculado total o parcial.

### 10.5 Liquidacion de propietario

1. El operador revisa cobros sin aplicar, gastos sin atribuir y otros pendientes del mes abierto.
2. Un usuario autorizado cierra el periodo mensual.
3. El operador selecciona propietario y periodo cerrado.
4. El sistema calcula aplicaciones por `appliedDate`, gastos por `paidDate` y movimientos informativos no liquidables.
5. El operador confirma la liquidacion o reabre el periodo si todavia es legal hacerlo.
6. Se guarda una instantanea con fuentes unicas y se genera PDF.
7. El propietario recibe aviso y consulta el documento.
8. El operador registra el pago de la liquidacion con referencia.

## 11. Experiencia web

### 11.1 Navegacion del equipo

- Dashboard.
- Cartera.
- Personas y empresas.
- Contratos.
- Reservas y calendario.
- Cobranzas.
- Gastos y mantenimiento.
- Propietarios y liquidaciones.
- Reportes.
- Documentos.
- Auditoria.
- Configuracion.

### 11.2 Dashboard

- Cargos y cobros del mes.
- Deuda vencida y proximos vencimientos.
- Gastos pagados y pendientes de aprobacion.
- Ocupacion tradicional y temporaria.
- Entradas, salidas y reservas proximas.
- Contratos por finalizar.
- Trabajos asincronos o notificaciones fallidas que requieren atencion.

### 11.3 Portal de propietario

- Resumen de cartera y participaciones.
- Ocupacion y contratos permitidos.
- Ingresos, egresos y saldos por periodo.
- Incidencias y gastos pendientes de aprobacion.
- Liquidaciones y documentos descargables.
- Vista estrictamente de consulta fuera de las decisiones de aprobacion.

### 11.4 Adaptabilidad y accesibilidad

- Los flujos principales deben funcionar desde 360 px de ancho.
- Tablas extensas deben ofrecer una representacion util en pantallas pequenas sin ocultar totales esenciales.
- Navegacion, formularios, dialogos y calendario deben ser utilizables con teclado.
- Estados, errores y resultados no deben comunicarse solamente mediante color.
- Los objetivos principales deben cumplir WCAG 2.2 nivel AA.

## 12. Arquitectura tecnica

### 12.1 Enfoque elegido

Se usara un monolito modular. Los dominios comparten despliegue y PostgreSQL, pero mantienen modulos, servicios e interfaces separados. La API y el worker se ejecutan como procesos independientes para aislar trafico interactivo de tareas periodicas o pesadas.

Esta opcion ofrece transacciones simples y operacion moderada para la escala esperada. Los limites REST y los eventos internos permiten extraer un modulo como servicio solamente si una necesidad real lo justifica.

### 12.2 Stack obligatorio

| Capa | Tecnologia |
| --- | --- |
| Gestor de paquetes | pnpm |
| Frontend | Next.js con App Router |
| Estilos y componentes | Tailwind CSS y shadcn/ui |
| Backend | NestJS |
| Validacion | Zod en formularios y limites de API |
| API | REST versionada y documentada con OpenAPI |
| ORM | Prisma ORM |
| Base de datos | PostgreSQL |
| Desarrollo local | PostgreSQL ejecutado con Docker |
| Archivos | DigitalOcean Spaces privado |
| Email | Resend |
| WhatsApp | Webhook HTTPS firmado hacia un bridge externo independiente del proveedor |

### 12.3 Estructura logica del monorepo

```text
apps/
  web/       Next.js, interfaz del equipo y portal de propietario
  api/       NestJS, REST, autenticacion y modulos de dominio
  worker/    Cargos, avisos, PDF, reintentos y tareas programadas
packages/
  contracts/ Esquemas Zod y contratos de intercambio compartidos
  config/    Configuracion comun de TypeScript, lint y herramientas
```

No se agrega un paquete compartido si solo tiene un consumidor. La logica de dominio permanece en el backend; compartir esquemas de entrada/salida no autoriza al frontend a reproducir reglas financieras.

### 12.4 Modulos NestJS

- `IdentityModule`.
- `OrganizationsModule`.
- `AuthorizationModule`.
- `PartiesModule`.
- `PortfolioModule`.
- `OwnershipModule`.
- `ContractsModule`.
- `BookingsModule`.
- `FinanceModule`.
- `MaintenanceModule`.
- `DocumentsModule`.
- `NotificationsModule`.
- `ReportsModule`.
- `AuditModule`.
- `JobsModule`.

Cada modulo debe exponer una interfaz clara, ser responsable de sus invariantes y evitar escribir directamente en tablas de otro modulo fuera de una operacion coordinada.

### 12.5 Frontend Next.js

- App Router y Server Components son la base para paginas y carga inicial.
- Componentes cliente se reservan para formularios, calendario, filtros interactivos y actualizaciones optimistas seguras.
- El frontend consume la API NestJS; no accede a Prisma ni PostgreSQL.
- Los datos financieros y privados deben solicitarse sin cache compartida entre usuarios.
- Las variables expuestas al navegador nunca contienen secretos.
- Formularios usan Zod y errores de API por campo, sin duplicar reglas de negocio complejas.

### 12.6 Persistencia PostgreSQL y Prisma

- Prisma es la via ordinaria de acceso a datos y migraciones.
- PostgreSQL debe mantener claves foraneas, indices, unicidad y restricciones de integridad.
- Operaciones monetarias, disponibilidad, titularidad y cierre usan transacciones.
- Las restricciones por organizacion deben incluirse en claves compuestas relevantes.
- Indices deben cubrir `organizationId`, fechas, estados, unidad, propietario y claves de idempotencia usadas en filtros frecuentes.
- Las migraciones de produccion son versionadas, revisables y no se ejecutan implicitamente al arrancar la aplicacion.

### 12.7 Worker, cola y eventos

- V1 usa una cola persistida en PostgreSQL y no requiere Redis.
- La transaccion de negocio guarda el cambio y un evento outbox inmutable con organizacion, agregado, version, correlacion, causacion y clave semantica.
- El dispatcher reclama con `FOR UPDATE SKIP LOCKED` en una transaccion corta. Cada job usa lease, fencing token, contador e historial append-only; se ejecuta fuera de la transaccion y un worker vencido no puede completar el intento.
- Los trabajos incluyen generacion de cargos, mora automatica, avisos, PDF y limpieza de artefactos temporales.
- Un trabajo debe declarar clave de idempotencia, cantidad maxima de intentos y politica de reintento.
- Los fallos agotados quedan visibles para diagnostico. Reejecutar crea una generacion enlazada con motivo y conserva la misma clave semantica; nunca borra intentos previos.
- Cada handler reabre contexto de tenant bajo principal `SYSTEM_JOB`, vuelve a autorizar el efecto permitido y comprueba suspension y revision del origen antes de actuar; nunca fabrica una membresia humana.

### 12.8 Archivos

- La API autoriza cada carga y descarga.
- Las cargas usan `UploadIntent`, clave staging no predecible y finalizacion idempotente; un objeto no queda disponible hasta verificar bytes, tamano, MIME, SHA-256 y malware.
- Los objetos finales usan claves no predecibles con prefijo logico por organizacion y versiones inmutables que el cliente no puede sobrescribir.
- Spaces permanece privado; no se guardan URL publicas permanentes.
- El checksum se calcula sobre los bytes finales; coincidencias solo alertan dentro de la misma organizacion y no comparten objetos.
- Los metadatos permanecen en PostgreSQL y el contenido binario en Spaces.

## 13. API y flujo de datos

### 13.1 API REST

- Prefijo inicial `/api/v1`.
- OpenAPI es parte del contrato entregable.
- Las entradas y salidas usan esquemas Zod estables.
- Listados usan paginacion, orden y filtros explicitos.
- Mutaciones sensibles aceptan clave de idempotencia.
- Los recursos nunca confian en un `organizationId` enviado por el cliente para autorizar acceso.
- Los esquemas rechazan campos desconocidos de seguridad; actor, membresia, organizacion, plano de acceso, estados derivados y auditoria se resuelven en servidor.
- Cambios incompatibles requieren una nueva version de API.

### 13.2 Flujo de una mutacion

1. Next.js envia la solicitud autenticada.
2. NestJS asigna identificador de correlacion.
3. La capa de identidad resuelve el principal declarado por el endpoint: identidad de usuario, membresia interna, grant de propietario, actor de plataforma o job de sistema, y la organizacion cuando corresponda.
4. Zod valida estructura y tipos.
5. La autorizacion verifica plano, permiso, alcance de datos y revision de contexto.
6. El modulo de dominio valida reglas de negocio.
7. Una transaccion vuelve a comprobar organizacion cuando corresponda, autoridad del principal, permisos o grant y versiones aplicables, y guarda datos, idempotencia, auditoria y outbox.
8. La API responde con el estado confirmado.
9. El worker procesa efectos secundarios sin reabrir la transaccion original.

### 13.3 Flujo de reporte

1. El usuario define filtros y criterio financiero.
2. La API valida alcance y ejecuta una consulta de lectura consistente que produce filas, totales, fecha de corte y hash.
3. La pantalla recibe esa instantanea y sus metadatos de filtros.
4. Si se solicita PDF, se guarda la misma instantanea con filtros, filas, totales, locale, zona y versiones, no solo una consulta para repetir despues.
5. El worker genera el PDF exclusivamente desde la instantanea, lo almacena en Spaces y notifica disponibilidad.
6. La descarga vuelve a verificar autorizacion.

## 14. Seguridad

### 14.1 Autenticacion y sesion

- Contrasenas con hash resistente y parametros revisables.
- Sesiones opacas server-side, rotables y revocables; la cookie solo lleva un identificador aleatorio.
- Cookies de sesion `HttpOnly`, `Secure` fuera de local y `SameSite=Lax`.
- Toda mutacion con cookie exige origen exacto permitido y token CSRF ligado a la sesion.
- Verificacion de email y tokens de recuperacion de un solo uso con expiracion.
- Rate limiting para login, recuperacion, invitaciones y endpoints sensibles.
- CORS restringido a origenes configurados.

### 14.2 Autorizacion

- Denegar por defecto cuando no existe permiso explicito.
- Verificar permiso y alcance en el backend, incluso si la interfaz oculta la accion.
- Separar permisos de plataforma, organizacion y portal de propietario.
- Exigir permisos reforzados para anulaciones, reaperturas, titularidades y exportacion de datos sensibles.
- Auditar elevaciones y cambios de acceso.

### 14.3 Proteccion de datos

- HTTPS obligatorio fuera de desarrollo local.
- Secretos fuera del repositorio y rotables.
- Base, respaldos y objetos cifrados en reposo mediante capacidades del proveedor.
- URL firmadas y breves para archivos.
- Logs sin contrasenas, tokens, documentos, RUC completos innecesarios ni contenido financiero sensible.
- Datos de una organizacion suspendida se conservan, pero no quedan accesibles a sus miembros.

## 15. Manejo de errores y resiliencia

### 15.1 Contrato de error

```json
{
  "code": "AVAILABILITY_CONFLICT",
  "message": "La unidad ya tiene una reserva o bloqueo para esas fechas.",
  "fieldErrors": {
    "checkIn": ["El intervalo entra en conflicto con una reserva confirmada."]
  },
  "correlationId": "identificador-seguro"
}
```

- `400` para solicitud mal formada.
- `401` para sesion ausente o invalida.
- `403` para un recurso visible dentro del alcance cuando falta permiso para la accion.
- `404` indistinguible para recurso inexistente o fuera del tenant/propietario autorizado.
- `409` para conflicto de negocio o concurrencia.
- `422` para validacion semantica por campos.
- `429` para limite de solicitudes.
- `503` para dependencia temporalmente no disponible.

### 15.2 Reglas de resiliencia

- Los mensajes al usuario deben explicar la accion posible sin exponer detalles internos.
- Un error de Resend, WhatsApp o Spaces no revierte movimientos financieros confirmados.
- Los efectos externos se reintentan desde la cola persistida.
- Las operaciones concurrentes de reservas, pagos y cierres deben detectar conflictos y responder sin corrupcion.
- Toda respuesta inesperada se registra con correlacion y se presenta como un mensaje seguro.
- Los trabajos fallidos y movimientos que requieren intervencion deben aparecer en una bandeja operativa.

## 16. Requisitos no funcionales

### 16.1 Escala y rendimiento

- Hasta 1.000 unidades por organizacion.
- Decenas de usuarios concurrentes por organizacion.
- Miles de movimientos mensuales por organizacion.
- Consultas habituales con objetivo `p95 <= 2 s` bajo la carga de referencia.
- Reportes simples con objetivo `p95 <= 5 s`.
- Reportes pesados y PDF procesados en segundo plano sin bloquear la interfaz.
- Listados paginados; no se cargan carteras completas en el navegador sin limite.
- La evidencia usa un fixture versionado de hasta 1.000 unidades, 24 meses, 5.000 efectos financieros mensuales y 30 usuarios concurrentes, con mezcla de endpoints, entorno y duracion publicados.

### 16.2 Disponibilidad operativa

- Health checks separados para web, API, worker, base y dependencias externas.
- Degradacion controlada: una caida de notificaciones no impide registrar cobros o gastos.
- Los trabajos pendientes sobreviven reinicios del worker.
- Las operaciones criticas usan transacciones y claves de idempotencia.

### 16.3 Respaldo y recuperacion

- PostgreSQL usa PITR con objetivo `RPO <= 15 min`, `RTO <= 8 h`, base cifrada diaria y retencion minima de 30 dias.
- Los objetos usan versionado o recuperacion equivalente por al menos 30 dias y conservan version, tamano y SHA-256 en metadatos.
- Prueba documentada de restauracion al menos una vez por trimestre.
- La restauracion empieza aislada y sin egress, aplica `RESTORE_HOLD` y verifica integridad entre metadatos y cada version de objeto antes de liberar jobs.

### 16.4 Observabilidad

- Logs estructurados con servicio, organizacion anonimizada cuando corresponda, usuario, ruta y correlacion.
- Metricas de latencia, errores, conexiones, trabajos, reintentos y proveedores externos.
- Alertas para errores sostenidos, antiguedad de cola, leases vencidos, dead letters, envios ambiguos, callbacks invalidos, uploads atascados, respaldos fallidos y almacenamiento no disponible.
- Auditoria funcional separada de logs tecnicos.

### 16.5 Compatibilidad y accesibilidad

- Soporte para las dos versiones estables mas recientes de Chrome, Edge, Firefox y Safari al momento de cada entrega.
- Diseno adaptable desde 360 px.
- WCAG 2.2 AA en autenticacion, cartera, cobros, reservas, gastos, liquidaciones y reportes.
- Formato local de fecha y PYG consistente en toda la interfaz y documentos.

## 17. Estrategia de pruebas

### 17.1 Pruebas unitarias

- Porcentajes y vigencias de copropiedad.
- Cronogramas de canon y generacion idempotente.
- Mora manual y automatica.
- Aplicaciones parciales y multiples de pagos.
- Saldos a favor.
- Reversiones y reembolsos externos parciales/totales.
- Depositos, deducciones y devoluciones.
- Imputacion y redondeo de gastos.
- Traslado de gasto a inquilino.
- Calculo y congelamiento de liquidaciones.
- Transiciones de contrato, reserva, gasto e incidencia.

### 17.2 Pruebas de integracion

- PostgreSQL real ejecutado en Docker.
- Claves foraneas, unicidad y restricciones compuestas.
- Transacciones de pagos y liquidaciones.
- Concurrencia de reservas para una misma unidad.
- Reclamo concurrente de trabajos del worker.
- Aislamiento de organizaciones en lecturas y escrituras.
- Migraciones reproducibles desde una base vacia y validacion de cada migracion nueva sobre el estado anterior del esquema en desarrollo.
- Integracion de metadatos con almacenamiento simulado compatible con Spaces.

### 17.3 Pruebas de contrato y API

- Entradas y respuestas contra esquemas Zod.
- Documento OpenAPI actualizado.
- Codigos de error estables.
- Paginacion, filtros y orden.
- Idempotencia de comandos sensibles.
- Autenticacion, permisos y alcance del propietario.

### 17.4 Pruebas de extremo a extremo

- Autorregistro, verificacion y creacion de organizacion.
- Carga manual e importacion CSV basica.
- Alta de cartera y copropiedad.
- Contrato, cargo mensual, pago parcial, mora y recibo.
- Reserva, bloqueo, check-in, no-show, cancelacion y reembolso manual.
- Incidencia, aprobacion, gasto y cargo al inquilino.
- Deposito recibido, deducido y devuelto.
- Liquidacion, PDF, aviso y registro de pago.
- Reporte mensual en pantalla y PDF.
- Restricciones del portal de propietario.

### 17.5 Pruebas de seguridad y regresion obligatorias

- Intentar acceder a cada recurso con un usuario de otra organizacion.
- Intentar elevar permisos manipulando solicitudes del navegador.
- Reejecutar jobs de cargos, mora, PDF y avisos.
- Enviar dos confirmaciones concurrentes para fechas superpuestas.
- Modificar titularidad y modalidad despues de periodos confirmados.
- Anular y reabrir movimientos con y sin permiso.
- Verificar que depositos nunca aparezcan como ingreso.
- Verificar que un gasto de ubicacion no se duplique al consolidar unidades.
- Verificar que un cargo que cruza meses se reconoce completo una sola vez por `recognitionDate`.
- Verificar que un reembolso reduce caja sin crear gasto ni borrar la recepcion original.

### 17.6 Escenarios de integracion para casos frontera

Cada escenario debe ejecutarse en el incremento que introduce la ultima capacidad involucrada. Los escenarios concurrentes usan PostgreSQL real y barreras de sincronizacion; no se consideran probados con mocks ni solicitudes estrictamente secuenciales.

| ID | Escenario obligatorio | Resultado esperado |
| --- | --- | --- |
| `BND-T01` | Intervalos contiguos y cambio de zona | Checkout, fin contractual, cambio de propietario y cambio de modalidad en una misma fecha no se superponen. Cambiar zona no mueve fechas ni periodos previos. |
| `BND-T02` | Autorregistro y aceptacion repetidos | Dos solicitudes concurrentes crean una organizacion, una membresia administradora, una auditoria y un resultado idempotente. La invitacion inicial se consume una vez y activa atomicamente una organizacion pendiente; una invitacion ordinaria no se acepta fuera de `ACTIVE`. |
| `BND-T03` | Pestana obsoleta y ultimo administrador | Un formulario de A enviado despues de cambiar a B no crea datos. Dos administradores no pueden revocarse de modo que el tenant quede sin raiz activa. |
| `BND-T04` | Identificador ajeno, conteo y cache | ID valido de B y aleatorio devuelven el mismo `404` desde A; listados, totales, busquedas y cache nunca revelan filas o metadatos cruzados. |
| `BND-T05` | Revocacion durante una mutacion | Revocar membresia, permiso o grant antes del commit hace fallar la operacion completa sin dominio, auditoria ni outbox parciales. |
| `BND-T06` | Copropiedad y redondeo | Reemplazar porcentajes concurrentemente produce una sola composicion valida. Repartos de pocos guaranies suman exactamente el original y no cambian al renombrar o reintentar. |
| `BND-T07` | Preview CSV obsoleto | Si cambia un codigo o referencia despues del preview, confirmar devuelve conflicto por fila e importa cero seleccionadas; reintentar un batch exitoso no crea ni renombra nada. |
| `BND-T08` | Contrato contra reserva, modalidad o archivo | Activar contrato, confirmar reserva/bloqueo, cambiar modalidad y archivar compiten bajo el mismo lock de unidad. Solo una mutacion incompatible gana y ningun perdedor crea cargo u outbox. Un bloqueo puede cruzar modalidad, pero sigue impidiendo ocupacion. |
| `BND-T09` | Ancla mensual y rescicion | Desde 31/01/2027 los inicios son 31/01, 28/02, 31/03; desde 30/01 son 30/01, 28/02, 30/03; desde 29/01/2028 son 29/01, 29/02, 29/03. Rescindir despues de iniciado un periodo conserva canon completo y detiene solo inicios posteriores. |
| `BND-T10` | Reserva, precio y cancelacion mixta | Confirmar congela total y crea un cargo. Cancelar con pagos externos y deposito libera fechas, revierte lo no ganado, crea penalidad, restaura retenido y reembolsa solo salidas reales una vez. |
| `BND-T11` | Salida anticipada y extension | El prefijo historico permanece ocupado, el sufijo se libera y una extension conflictiva no cambia fechas ni crea cargo parcial. |
| `BND-T12` | Sobreaplicacion concurrente | Dos usos del mismo pago, cargo o deposito nunca dejan saldo negativo; una operacion confirma y la otra recibe `409` sin recorte automatico. |
| `BND-T13` | Reversion despues del corte | Una aplicacion de agosto revertida parcialmente en septiembre sigue completa en el corte de agosto y aparece como efecto inverso en septiembre. |
| `BND-T14` | Aplicacion y reversion de deposito | Movimiento retenido, fuente interna y aplicacion confirman o fallan juntos. Revertir restaura deuda y fondo exactos sin segunda entrada de caja. |
| `BND-T15` | Cierre contra movimiento | Cierre y confirmacion compiten por el mismo periodo: el movimiento queda incluido antes del cierre o falla despues. No se abre un mes anterior para eludir el cierre. |
| `BND-T16` | Liquidacion obsoleta y copropiedad | Preview no reclama fuentes. Dos confirmaciones del mismo propietario-periodo no duplican revision; cada copropietario reclama solo su efecto y un preview alterado devuelve `STALE_PREVIEW`. |
| `BND-T17` | Ajuste tras liquidacion pagada | La liquidacion y PDF pagados no cambian; la correccion usa instantanea original y aparece enlazada en el periodo abierto de la `businessDate` del comando. |
| `BND-T18` | Politica, umbral y aprobadores | Importe igual al umbral exige aprobacion. Politica requerida sin parte o representante es error; representantes duplicados producen una sola decision por `Party`. |
| `BND-T19` | Real menor y emergencia | Menor importe sobre las mismas lineas conserva aprobacion; nueva linea o alcance exige revision. Override sin permiso, motivo o evidencia no permite incurrir ni pagar. |
| `BND-T20` | Traslado y atribucion tardia | Dos traslados no superan el gasto. Emitir cargo no compensa costo; el cobro recupera para la instantanea del gasto. Imputar despues del cierre crea ajuste sin duplicar caja. |
| `BND-T21` | Pantalla y PDF mutable | Tras solicitar PDF se modifica un pago o plantilla; el PDF conserva exactamente filas, totales y version vistos, y una nueva consulta refleja el cambio. |
| `BND-T22` | Finalizacion de upload | Reusar URL staging, finalizar dos veces o competir con limpieza nunca modifica la version disponible ni crea dos documentos; archivo no verificado permanece inaccesible. |
| `BND-T23` | Timeout, firma y callbacks de mensaje | Timeout despues de aceptacion se reintenta con misma clave y payload y el bridge devuelve el resultado estable. Firma alterada, timestamp vencido o key ID desconocido se rechaza. Callbacks duplicados o fuera de orden se guardan una vez por evento y no hacen retroceder entrega; ambiguedad vencida requiere revision manual. |
| `BND-T24` | Lease y worker antiguo | Tras vencer lease otro worker completa el job; el worker anterior no puede marcarlo exitoso. Reejecutar conserva intentos y no duplica el efecto semantico. |
| `BND-T25` | Suspension y reactivacion | Durante suspension no hay acceso, URLs ni envios. Jobs contables deterministas conservan historia; al reactivar se descartan recordatorios obsoletos y no se duplican ocurrencias. |
| `BND-T26` | Restauracion sin reenvio | Un backup con outbox pendiente restaurado despues de un envio real queda en `RESTORE_HOLD`; no sale egress hasta reconciliar y cada objeto referenciado pasa tamano y SHA-256. |
| `BND-T27` | Ocupacion sin capacidad vendible | Bloqueos salen del denominador, contratos/reservas ocupan y archivo elimina capacidad. Si todo esta bloqueado o archivado, ocupacion es N/A. |
| `BND-T28` | CSRF, origen y campos controlados | Mutacion con cookie sin origen exacto o token ligado a sesion falla antes del dominio. Inyectar organizacion, actor, grant o estado en el payload se rechaza y no cambia el principal resuelto. |
| `BND-T29` | Mora omitida y redondeo | El cierre detecta una ocurrencia de mora sin cargo, concesion o excepcion. Una tasa en partes por millon redondea mitad hacia arriba una sola vez y dos workers producen un unico recargo. |
| `BND-T30` | Correcciones de cada efecto de caja | Corregir recepcion falsa, reembolso falso, pago de gasto o desembolso erroneo, y registrar devolucion real de proveedor conserva originales, impacta solo por `postingDate` y hace cuadrar el flujo con signos sin crear ingreso o gasto duplicado. |
| `BND-T31` | Documento de expropietario | Con grant vigente, un expropietario descarga documento historico si audiencia y titularidad intersectan, y siempre su propia liquidacion aunque se emita por ajuste posterior. No ve documentos de nuevos propietarios; revocar el grant corta ambos accesos. |
| `BND-T32` | No-show con fondos | Al llegar check-in sin ingreso, no-show libera todo el intervalo, corrige una vez el cargo de estadia, crea solo la penalidad configurada en `noShowDate`, restaura deposito aplicado y concilia fondos externos sin reembolso ficticio. |
| `BND-T33` | Extension exitosa | Una reserva `[10/08, 12/08)` extendida sin conflicto hasta 14/08 conserva el prefijo, ocupa el sufijo y crea una sola vez un cargo adicional con `recognitionDate = 12/08`. |

## 18. Criterios de aceptacion de V1

### 18.1 Cartera configurable

- Se crea una ubicacion U1 con diez unidades.
- El sistema sugiere nombres y el usuario puede cambiarlos a D1, D2, PB9, PB10 u otros sin perder relaciones.
- Cada unidad recibe un tipo fisico configurable.
- D1 a D4 operan como tradicional, D5 y D6 como temporaria y PB9/PB10 como comercial.
- D5 puede pasar de temporaria a tradicional en una fecha valida y conserva toda su historia.
- D7 puede marcarse en venta y continuar alquilada.

### 18.2 Cobros y gastos mensuales

- En agosto D1 muestra PYG 2.000.000 devengados y el cobro registrado por separado.
- D1 muestra PYG 70.000 de plomeria con detalle de cambio de canilla.
- D2 desocupada aparece con PYG 0 de ingreso y PYG 500.000 de mantenimiento.
- Varias lineas de D2 deben sumar exactamente PYG 500.000.
- El usuario puede consultar solo D1, toda la ubicacion o toda la cartera del propietario.

### 18.3 Gastos de ubicacion

- Una reparacion de porton del Edificio 1 queda sin distribuir por defecto.
- El usuario puede asignarla a una unidad, a varias unidades o a todas por partes iguales.
- Sin distribucion, aparece una sola vez en ubicacion/organizacion y no altera liquidaciones de propietarios.
- Si se atribuye a unidades, cada propietario recibe solamente su participacion correspondiente.

### 18.4 Contrato y mora

- Un contrato activo genera un solo cargo por periodo aunque el worker se ejecute varias veces.
- El cronograma cambia el canon en la fecha pactada sin alterar cargos anteriores.
- Un pago parcial reduce el saldo correcto y genera recibo interno.
- El modo manual permite agregar recargo; el automatico genera un unico recargo despues de la gracia.

### 18.5 Reserva temporaria

- El sistema permite confirmar una reserva disponible.
- Una segunda reserva superpuesta es rechazada aun si dos usuarios confirman al mismo tiempo.
- Una cancelacion libera fechas y concilia atomicamente cargo, aplicaciones, deposito, penalidad y salidas reales.
- La retencion se aplica a un cargo de penalidad y el resto se reembolsa desde saldo externo no aplicado.
- Un bloqueo evita reservas sin generar ingresos.

### 18.6 Copropiedad y liquidacion

- Una unidad con dos propietarios exige participaciones que sumen 100 %.
- Cambiar porcentajes en septiembre no modifica cargos o liquidaciones de agosto.
- Un cargo mensual cuyo servicio inicia antes de un cambio de propietario conserva las participaciones vigentes al inicio; V1 no lo prorratea automaticamente.
- La liquidacion usa aplicaciones por `appliedDate` y gastos por `paidDate`, sin volver a incluir una fuente ya liquidada.
- Depositos y cobros no aplicados se informan, pero no aumentan el neto liquidable.
- Confirmar la liquidacion congela sus lineas y genera el mismo total en PDF.
- Una liquidacion pagada no cambia al registrar una correccion tardia; el ajuste aparece enlazado en el periodo abierto de la `businessDate` de correccion.

### 18.7 Depositos y fechas de caja

- Recibir un deposito aumenta entrada de caja y fondos retenidos, pero no ingreso.
- Aplicar parte del deposito a un cargo reduce el saldo retenido, cancela deuda y no crea una nueva entrada de caja.
- Devolver el deposito se muestra como salida de caja no operativa y no como gasto.
- Un pago recibido en agosto y aplicado en septiembre aparece como entrada en agosto y como cobro aplicado en septiembre, sin duplicarse.
- Un reembolso de septiembre por un pago de agosto aparece como salida en septiembre y no reescribe la entrada de agosto.
- Si un pago se aplica parcialmente y se reembolsa todo el remanente, su cobro no aplicado queda en cero y la aplicacion conserva su saldo correcto.

### 18.8 Aprobacion y traslado de gastos

- Un gasto cuyo importe materializado alcanza o supera el umbral solicita a las partes aprobadoras configuradas.
- Un propietario puede aprobar o rechazar desde su portal.
- Una emergencia exige permiso, motivo y evidencia si omite aprobacion.
- Un gasto trasladado al inquilino genera un cargo enlazado por el importe elegido y no se recupera dos veces.
- Aumentar el total o cambiar unidades/imputacion despues de aprobar invalida la aprobacion y exige una nueva version.

### 18.9 Cierre de periodos

- Cerrar agosto impide retrofechar cargos, pagos, aplicaciones, reversiones, reembolsos, gastos, atribuciones o depositos dentro de agosto.
- Reabrir agosto conserva las liquidaciones anteriores como versiones reemplazadas si ninguna fue pagada.
- Si una liquidacion de agosto ya fue pagada, la correccion se registra como ajuste en septiembre y no reescribe agosto.

### 18.10 Aislamiento y permisos

- Un usuario de la organizacion A no puede descubrir, consultar ni modificar identificadores validos de la organizacion B.
- Un propietario vigente ve su cartera autorizada; un expropietario conserva solo sus movimientos, liquidaciones y documentos historicos dirigidos a el.
- Una accion oculta en la interfaz tambien es rechazada por la API cuando falta permiso.
- Un rol interno permite acciones sobre toda la organizacion; V1 no debe aparentar que limita a un miembro por ubicacion.

## 19. Riesgos y mitigaciones

| Riesgo | Mitigacion obligatoria |
| --- | --- |
| Fuga de datos entre organizaciones | Contexto de sesion, filtros obligatorios, restricciones compuestas y pruebas cruzadas. |
| Doble reserva por concurrencia | Validacion transaccional y bloqueo por unidad al confirmar. |
| Duplicacion de cargos o mensajes | Claves unicas de idempotencia, outbox y worker reintentable. |
| Alteracion de historia financiera | Efectos correctivos enlazados, instantaneas y prohibicion de borrar o reescribir confirmados. |
| Doble conteo de gastos generales | Separar alcance, imputacion y atribucion; mostrar "sin imputar". |
| Liquidacion incorrecta tras cambio de propietario | Instantanea de participacion por cargo/gasto y liquidacion inmutable. |
| Dependencia de WhatsApp | Webhook firmado, contrato probado, canal deshabilitado sin bridge y estados de entrega desacoplados. |
| PDF distinto de pantalla | Un unico servicio de consulta y filtros normalizados para ambos formatos. |
| Worker detenido | Cola persistida, health check, metricas, alertas y reejecucion autorizada. |
| Perdida de documentos | Spaces privado, checksum, respaldo y prueba de restauracion. |

## 20. Enfoques considerados

### 20.1 Monolito modular con API y worker separados

Elegido. Mantiene transacciones simples, despliegue razonable y limites de dominio claros. La API queda disponible para V2 movil y los procesos pesados no bloquean solicitudes web.

### 20.2 Monolito tradicional por capas

Descartado. Reduce estructura inicial, pero favorece el acoplamiento entre contratos, reservas, gastos, propietarios y permisos a medida que crece el producto.

### 20.3 Microservicios

Descartado para V1. Agrega mensajeria distribuida, consistencia eventual, observabilidad y despliegues complejos sin una necesidad de escala que lo justifique.

## 21. Limites de planificacion y entregas

Este archivo es la especificacion integral de producto, no un unico ciclo de implementacion. V1 debe construirse mediante incrementos ordenados; cada incremento recibira su propio plan detallado, pruebas y puerta de aceptacion. No se debe crear un plan de implementacion monolitico para todos los modulos a la vez.

| Incremento | Alcance cerrado | Dependencia | Puerta de aceptacion |
| --- | --- | --- | --- |
| 0. Plataforma segura | Monorepo, configuracion, PostgreSQL local, autenticacion, email transaccional minimo de identidad, organizaciones, membresias, permisos, aislamiento, auditoria base, API, outbox, jobs con lease y restauracion en hold. | Ninguna. | Dos organizaciones operan sin acceso cruzado; invitacion/verificacion, API, migraciones, auditoria, cola y recuperacion de jobs tienen pruebas de integracion. |
| 1. Cartera | Partes, ubicaciones, unidades, nombres sugeridos, tipos, modalidades, venta, titularidades, portal propietario minimo, importacion CSV basica y sustrato minimo de archivos privados con `UploadIntent`, metadatos y descarga autorizada. | Incremento 0. | Se reproduce U1 con diez unidades, modalidades mixtas, copropiedad e historia sin inconsistencias; un adjunto privado no verificado permanece inaccesible. |
| 2. Alquiler tradicional y finanzas | Contratos, cronogramas, cargos, mora, pagos, aplicaciones, recibos, depositos, periodos y reportes financieros base. | Incremento 1. | Cargo idempotente, pago parcial, fechas de caja/aplicacion, deposito y cierre mensual cuadran bajo concurrencia. |
| 3. Gastos y propietarios | Incidencias, aprobaciones versionadas, gastos, imputaciones, traslado al inquilino, liquidaciones y portal completo de propietario. | Incremento 2. | Casos D1/D2, gasto de porton, copropiedad y liquidacion producen totales trazables en pantalla. |
| 4. Alquiler temporario | Calendario, bloqueos, reservas, tarifas, cargos, check-in/out, cancelacion y uso de depositos. | Incrementos 1, 2 y 3. | Reservas concurrentes no se superponen y cancelaciones concilian cargos, depositos, liquidaciones y fechas. |
| 5. Documentos, comunicaciones y endurecimiento | Plantillas/PDF, experiencia documental completa y endurecimiento de Spaces, comunicaciones de negocio por Resend, webhook WhatsApp, reportes completos, observabilidad, rendimiento, accesibilidad y validacion final de respaldo/restauracion. | Incrementos 0 a 4. | Todos los criterios de V1, PDF/pantalla, rendimiento, seguridad y restauracion pasan de extremo a extremo. |

La trazabilidad minima entre requisitos e incrementos es:

- Incremento 0: `ORG`, `IAM`, base de `AUD` y fundamentos de las secciones 12 a 15 que necesitan los incrementos posteriores.
- Incremento 1: `PTY`, `PRT`, `OWN`, `IMP`, visibilidad patrimonial basica y la parte de `DOC` necesaria para adjuntos privados.
- Incremento 2: `CTR`, `MOR`, `FIN`, `DEP`, periodos financieros y reportes base de deuda/caja.
- Incremento 3: `EXP`, `MNT`, `LIQ`, portal financiero de propietario y caso mensual D1/D2.
- Incremento 4: `RSV` y sus integraciones con cargos, pagos, depositos y disponibilidad.
- Incremento 5: generacion y experiencia completa de `DOC`, comunicaciones de negocio de `NTF`, todos los reportes restantes y requisitos no funcionales finales.

Los casos frontera se introducen donde nace su invariante y se vuelven a ejecutar en todo incremento que la atraviesa:

- Incremento 0 introduce `BND-001` a `BND-010` en el contexto de identidad, `BND-IAM-01` a `BND-IAM-08` y `BND-IAM-10`, `BND-JOB-*`, las porciones de identidad de `BND-NTF-01` a `BND-NTF-03` y la porcion PostgreSQL/hold de `BND-OPS-*`.
- Incremento 1 introduce `BND-PRT-*`, `BND-IMP-*`, grants y visibilidad historica minima, `BND-DOC-01`, `BND-DOC-02`, `BND-DOC-05` y recuperacion de objetos; reutiliza las convenciones transversales sin anticipar finanzas.
- Incremento 2 introduce `BND-CTR-*`, `BND-MOR-*`, `BND-FIN-*`, `BND-DEP-*`, `BND-PER-*`, `BND-REP-*` y el lock de unidad de `BND-AVL-01`/`BND-AVL-02`; extiende jobs para efectos financieros.
- Incremento 3 introduce `BND-IAM-09`, `BND-EXP-*`, `BND-LIQ-*`, evidencia documental de aprobacion y ajustes de atribucion tardia.
- Incremento 4 completa `BND-AVL-*`, introduce `BND-RSV-*` y vuelve a ejecutar las invariantes financieras, de gastos y liquidaciones atravesadas por reservas.
- Incremento 5 completa `BND-DOC-*` y `BND-NTF-*`, endurece `BND-JOB-*`/`BND-OPS-*` y repite end-to-end todos los escenarios `BND-T*`.

El incremento 5 debe planificarse en subplanes 5A documentos/Spaces, 5B comunicaciones y 5C reportes/endurecimiento. Puede desplegarse progresivamente, pero V1 no termina hasta completar las tres puertas.

Las interfaces entre modulos se definen en el incremento que las necesita. Los incrementos posteriores no justifican crear abstracciones o tablas anticipadas fuera de las decisiones ya fijadas en esta especificacion.

## 22. Evolucion posterior

La arquitectura debe permitir incorporar sin redisenar el dominio central:

- Aplicacion movil para equipo y propietarios.
- Portal de inquilinos y huespedes.
- Flujo completo de compraventa.
- Facturacion electronica paraguaya.
- Pasarela de pagos y conciliacion bancaria.
- Sincronizacion con plataformas de reservas.
- Firma electronica.
- Multimoneda y cotizaciones.
- Comisiones automaticas de administradora.
- Planes, limites y cobro de suscripcion SaaS.
- Mantenimiento preventivo, proveedores y presupuestos avanzados.

Estas capacidades no forman parte de los criterios de aceptacion de V1.

Salvo la API versionada para una app movil y el webhook WhatsApp ya exigidos por V1, esta lista no debe impulsar implementacion anticipada.

## 23. Definicion de terminado para V1

V1 se considera terminada cuando:

- Todos los requisitos incluidos tienen evidencia de aceptacion.
- Las pruebas unitarias, de integracion, API, E2E y seguridad obligatorias pasan.
- Los casos de aislamiento, concurrencia e idempotencia pasan bajo PostgreSQL real.
- La pantalla y los PDF cuadran para los casos financieros de referencia.
- Se cumplen los objetivos de rendimiento bajo la carga definida.
- Se completo una restauracion de respaldo verificada.
- OpenAPI, variables de entorno, operacion del worker y procedimientos de recuperacion estan documentados.
- No existen defectos criticos o altos abiertos que puedan perder dinero, duplicar reservas, filtrar datos o alterar historia.

Este documento define el producto, sus reglas, casos frontera y limites de cada entrega. Las tareas tecnicas se planificaran un incremento por vez, comenzando por el incremento 0.
