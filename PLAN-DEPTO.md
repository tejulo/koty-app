# PLAN-DEPTO

Especificacion funcional y tecnica para la primera version de un sistema SaaS de administracion de alquileres.

| Dato | Valor |
| --- | --- |
| Estado | Diseno aprobado durante brainstorming; pendiente de revision final del archivo |
| Fecha | 2026-08-08 |
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
- Contratos tradicionales y comerciales, uno por unidad.
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
- Al terminar su titularidad, conserva acceso solo a sus liquidaciones, movimientos atribuidos y documentos historicos dirigidos a el; no ve ocupacion, partes ni documentos posteriores.
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
| Estado operativo | Disponibilidad, ocupacion, reserva, mantenimiento o inactividad de una unidad. |
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
| `Role` / `Permission` | Autorizacion configurable por accion dentro de una organizacion. |
| `Party` | Datos de persona fisica o juridica y sus roles de negocio. |
| `Location` | Agrupa unidades y recibe gastos generales. |
| `Unit` | Bien operable, codigo, nombre, tipo fisico y estado administrativo. |
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
| `Document` | Metadatos, pertenencia, version y clave privada en Spaces. |
| `Notification` | Canal, destinatario, plantilla, estado e intentos de entrega. |
| `AuditEvent` | Actor, accion, entidad, cambios relevantes y correlacion. |

## 7. Reglas e invariantes

### 7.1 Aislamiento multiempresa

- Toda entidad de negocio debe incluir `organizationId` directo o una relacion que lo haga verificable.
- La organizacion activa se obtiene de la sesion autenticada, nunca de un valor confiado del formulario.
- Toda consulta y mutacion debe aplicar el alcance de organizacion antes de evaluar permisos funcionales.
- Las relaciones criticas deben usar restricciones compuestas que impidan referencias entre organizaciones.
- Las pruebas automatizadas deben intentar accesos cruzados con identificadores validos de otra organizacion.

### 7.2 Dinero y fechas

- Todos los importes se guardan como enteros PYG; no se usan numeros de punto flotante.
- V1 no convierte monedas ni acepta movimientos en una moneda distinta de PYG.
- Los instantes se guardan en UTC y se presentan en la zona horaria de la organizacion.
- Fechas contractuales, periodos y noches se modelan como fechas civiles, sin conversion accidental de zona horaria.
- Los redondeos de prorrateo deben conservar el total original. La diferencia entera se asigna de forma determinista y queda visible.
- Todo cargo tiene `recognitionDate`. El devengado, periodo financiero y titularidad se determinan por esa fecha.
- Para alquiler mensual `recognitionDate` es el inicio del periodo de servicio; para reserva es check-in; para mora, servicio o gasto trasladado es la fecha efectiva del hecho que lo origina.
- V1 reconoce el cargo completo en `recognitionDate` y no prorratea automaticamente intervalos que cruzan meses. Si el acuerdo exige reparto, se emiten cargos separados.

### 7.3 Historia e inmutabilidad

- Los registros financieros confirmados no se eliminan ni se sobrescriben para ocultar su valor original.
- Una correccion financiera usa anulacion con motivo y un contramovimiento o una nueva version segun corresponda.
- Los contratos, plantillas, titularidades y modalidades conservan intervalos de vigencia.
- Un cambio de titularidad o modalidad no recalcula cargos, gastos ni liquidaciones ya confirmados.
- Los documentos generados guardan la version de plantilla y los datos usados al momento de generacion.

Los ciclos financieros obligatorios son:

- Un cargo pasa de borrador a emitido o anulado. Abierto, parcialmente pagado, pagado y vencido son estados de cobro derivados de sus aplicaciones y vencimiento.
- Un pago externo pasa de borrador a confirmado o anulado. Al confirmar se fijan importe y fecha efectiva de recepcion.
- Una fuente interna por deposito se crea confirmada, sin entrada de caja, con fecha efectiva igual a su aplicacion.
- Una aplicacion pasa de confirmada a revertida. Tiene fecha efectiva propia, no anterior a la disponibilidad de su fuente, y nunca se edita en sitio.
- Un reembolso de pago externo pasa de borrador a confirmado o anulado. Al confirmar fija importe y `refundedAt`.
- Un movimiento de deposito pasa de borrador a confirmado o anulado. Su tipo determina si aumenta o reduce el saldo retenido.
- Un gasto conserva `incurredAt` desde que pasa a incurrido y `paidAt` desde que pasa a pagado. Pagarlo no elimina su condicion de incurrido.
- Solamente estados emitidos o confirmados participan en reportes; los estados derivados no sustituyen el historial de movimientos.

### 7.4 Titularidad

- Una unidad puede tener uno o varios propietarios.
- Las participaciones vigentes de una unidad deben sumar exactamente 100 %.
- No pueden existir intervalos de titularidad superpuestos que produzcan una suma distinta de 100 %.
- Cargos y gastos que alimentan liquidaciones conservan una instantanea de la participacion aplicable.
- La participacion de un cargo se determina por `recognitionDate`; para alquiler mensual coincide con el inicio del periodo de servicio.
- Un acuerdo que requiera prorrateo dentro del periodo se representa mediante cargos o ajustes separados.
- La participacion de un gasto se determina por `incurredAt`.
- Una imputacion posterior usa una `allocationEffectiveDate` que por defecto coincide con `incurredAt`; nunca usa la fecha en que el usuario termino de procesarla.
- Elegir "todas las unidades activas" materializa las unidades existentes en `allocationEffectiveDate`, de modo que altas o bajas posteriores no cambian el resultado.

### 7.5 Disponibilidad

- Una reserva confirmada ocupa el intervalo `[check-in, check-out)`; permite salida y nueva entrada el mismo dia.
- Un contrato tradicional o comercial ocupa desde su fecha inicial hasta el final de su fecha final inclusive.
- Una unidad puede tener varios contratos historicos, pero no dos contratos tradicionales/comerciales activos con fechas superpuestas.
- Un contrato tradicional/comercial activo tampoco puede superponerse con reservas confirmadas o bloqueos.
- Las reservas temporarias no superpuestas se permiten solamente durante una vigencia de modalidad temporaria.
- La confirmacion de disponibilidad debe ejecutarse con control transaccional por unidad para impedir carreras concurrentes.
- Un cambio futuro de modalidad se rechaza si entra en conflicto con contratos, reservas o bloqueos vigentes para ese intervalo.

### 7.6 Idempotencia

- Un cargo periodico se identifica de manera unica por contrato, periodo y concepto.
- Una notificacion automatica se identifica por evento, destinatario, canal y plantilla.
- Los comandos sensibles aceptan una clave de idempotencia cuando puedan repetirse por red o worker.
- Reintentar una operacion no puede duplicar cargos, pagos, liquidaciones, PDF ni mensajes.

### 7.7 Periodos financieros

- Cada organizacion tiene un unico periodo por mes calendario, identificado por `YYYY-MM`; los periodos no se superponen.
- Un periodo abierto admite movimientos con fecha efectiva dentro del mes. Cerrarlo congela cargos por `recognitionDate`, pagos por recepcion, aplicaciones por `appliedAt`, reembolsos por `refundedAt`, gastos por `incurredAt`/`paidAt` y depositos por fecha de movimiento.
- El cierre evalua la fecha efectiva de cada movimiento, no la fecha original de su entidad. Un gasto incurrido en agosto puede pagarse en septiembre abierto sin modificar su importe ni `incurredAt` de agosto.
- Los reportes pueden consultar meses abiertos o cerrados, pero una liquidacion confirmada solo usa un periodo cerrado.
- Si no existe una liquidacion pagada, un usuario autorizado puede reabrir el mes. Las liquidaciones confirmadas quedan marcadas para reemision y sus versiones anteriores se conservan.
- Si alguna liquidacion del mes ya fue pagada, el periodo no se reabre para alterar su neto; la correccion se registra como ajuste enlazado en el siguiente periodo abierto.
- Un movimiento omitido de un mes cerrado no puede retrofecharse sin reapertura. Si el mes no puede reabrirse, se registra en el periodo abierto como ajuste que referencia fecha y origen reales.
- Un movimiento atribuible a propietario puede aparecer en una sola linea de liquidacion activa; una restriccion evita volver a liquidarlo.

### 7.8 Visibilidad historica del propietario

- La visibilidad financiera se decide por las instantaneas de participacion y las lineas atribuidas al propietario.
- La vista operativa actual de una unidad exige una titularidad vigente.
- Una titularidad finalizada no habilita datos de inquilinos, huespedes, incidencias o contratos posteriores.
- Cada documento declara audiencia: solo equipo, propietarios afectados o partes seleccionadas.
- Un propietario historico ve un documento solo si fue incluido en su audiencia y la fecha efectiva del documento intersecta su titularidad, o si el documento pertenece a una liquidacion propia.

## 8. Requisitos funcionales

### 8.1 Organizaciones y onboarding

- `ORG-01`: el superadministrador debe poder crear una organizacion y enviar invitacion a su primer administrador.
- `ORG-02`: una persona debe poder autorregistrarse, verificar su email y crear una organizacion activa.
- `ORG-03`: el sistema debe impedir el uso de una organizacion suspendida y conservar todos sus datos.
- `ORG-04`: cada organizacion debe configurar nombre legal y comercial, RUC opcional, direccion, contactos, logo, zona horaria y prefijo de recibos.
- `ORG-05`: la organizacion debe configurar dias de aviso, reglas de mora, categorias, tipos de unidad, medios de pago y politicas de aprobacion.
- `ORG-06`: el sistema debe incluir valores iniciales utiles sin impedir su edicion o desactivacion.
- `ORG-07`: la facturacion del SaaS debe permanecer fuera del flujo de negocio de V1.

### 8.2 Identidad, roles y permisos

- `IAM-01`: el acceso debe usar email verificado y contrasena.
- `IAM-02`: deben existir invitacion, aceptacion, recuperacion de contrasena y cierre de sesiones activas.
- `IAM-03`: un usuario puede pertenecer a varias organizaciones y debe elegir un contexto activo.
- `IAM-04`: el administrador puede crear roles con permisos por accion.
- `IAM-05`: el sistema debe ofrecer plantillas editables de administrador, operador, cobranzas y mantenimiento.
- `IAM-06`: el acceso de propietario debe estar limitado por sus titularidades, ademas de sus permisos.
- `IAM-07`: cambios de roles, permisos, miembros y acceso de propietario deben quedar auditados.
- `IAM-08`: los roles internos de V1 habilitan acciones sobre toda la organizacion; el alcance por ubicacion o unidad queda fuera de V1.

### 8.3 Partes

- `PTY-01`: una parte puede ser persona fisica o juridica.
- `PTY-02`: debe admitir nombre, documento o RUC, contactos, direccion, observaciones y archivos.
- `PTY-03`: una misma parte puede actuar en varios roles sin duplicar su identidad.
- `PTY-04`: el sistema debe detectar posibles duplicados dentro de la organizacion por documento, RUC, email o telefono, permitiendo resolverlos de forma explicita.
- `PTY-05`: una parte referenciada historicamente se archiva; no se elimina fisicamente.

### 8.4 Ubicaciones y unidades

- `PRT-01`: una organizacion puede crear cualquier cantidad de ubicaciones dentro del limite operativo contratado externamente.
- `PRT-02`: una ubicacion debe admitir nombre, codigo, direccion, descripcion, contactos, archivos y estado activo/inactivo.
- `PRT-03`: una ubicacion puede contener una o muchas unidades.
- `PRT-04`: la unidad debe admitir codigo unico dentro de la ubicacion, nombre visible editable, tipo fisico, descripcion y archivos.
- `PRT-05`: si el usuario no asigna un nombre, el sistema debe sugerir `<prefijo-ubicacion>-<secuencia>`; si no existe prefijo, `Unidad <secuencia>`.
- `PRT-06`: el usuario puede editar el nombre sugerido sin alterar identificadores internos ni historia.
- `PRT-07`: los tipos fisicos deben ser catalogos configurables, por ejemplo casa, duplex, departamento, cabana y salon comercial.
- `PRT-08`: la modalidad debe registrarse por intervalos tradicional, temporaria o comercial.
- `PRT-09`: la unidad puede marcarse en venta sin bloquear contratos o reservas.
- `PRT-10`: archivar una unidad debe impedir nuevas operaciones y conservar las anteriores.
- `PRT-11`: el sistema debe mostrar disponibilidad y ocupacion derivadas de contratos, reservas, bloqueos y estados administrativos.

### 8.5 Titularidad y copropiedad

- `OWN-01`: una unidad debe admitir una o varias partes propietarias con porcentajes.
- `OWN-02`: toda titularidad debe tener fecha de inicio y puede tener fecha de fin.
- `OWN-03`: la suma de porcentajes vigentes debe ser 100 % antes de activar operaciones financieras nuevas.
- `OWN-04`: un cambio de propietarios debe conservar la distribucion historica de periodos anteriores.
- `OWN-05`: el administrador debe poder designar usuarios de portal vinculados a cada parte propietaria.
- `OWN-06`: los reportes del propietario deben respetar su porcentaje historico para cada periodo.

### 8.6 Contratos tradicionales y comerciales

- `CTR-01`: cada registro de contrato debe referenciar exactamente una unidad; una unidad puede conservar varios contratos historicos no superpuestos.
- `CTR-02`: una parte puede mantener contratos separados sobre varias unidades.
- `CTR-03`: el contrato debe admitir uno o varios inquilinos responsables y garantes opcionales.
- `CTR-04`: debe contener modalidad, fechas, dia de vencimiento, cronograma de importes, deposito, regla de mora y documentos.
- `CTR-05`: los estados persistidos deben ser borrador, activo, finalizado y rescindido; "proximo a vencer" es un indicador derivado por fecha y configuracion.
- `CTR-06`: activar un contrato debe validar unidad, titularidad, partes, cronograma y ausencia de conflictos.
- `CTR-07`: el cronograma debe permitir cambios de canon pactados con fecha futura.
- `CTR-08`: cambiar el cronograma no debe modificar cargos ya emitidos; una correccion retroactiva requiere ajuste auditable.
- `CTR-09`: el worker debe generar los cargos mensuales de forma idempotente.
- `CTR-10`: finalizar o rescindir detiene cargos futuros, pero conserva deuda, pagos, documentos y deposito.
- `CTR-11`: una renovacion debe crear un nuevo periodo contractual o contrato enlazado, sin sobrescribir el anterior.
- `CTR-12`: el sistema debe avisar proximos vencimientos y contratos por finalizar segun configuracion.
- `CTR-13`: contratos tradicionales y comerciales no pueden superponerse entre si para una unidad.
- `CTR-14`: un contrato tradicional/comercial no puede superponerse con una reserva confirmada o bloqueo; la marca en venta no participa en esta validacion.

### 8.7 Mora

- `MOR-01`: la organizacion define una regla por defecto y cada contrato puede reemplazarla.
- `MOR-02`: el modo manual debe calcular dias de atraso y permitir agregar un cargo de mora con detalle.
- `MOR-03`: el modo automatico debe admitir dias de gracia y un recargo unico fijo o porcentual sobre saldo vencido.
- `MOR-04`: el recargo automatico debe ser idempotente por cargo original y regla aplicada.
- `MOR-05`: el usuario con permiso debe poder anular un recargo con motivo, sin ocultar su historia.

### 8.8 Reservas temporarias

- `RSV-01`: el calendario debe mostrar reservas y bloqueos por unidad y rango de fechas.
- `RSV-02`: una reserva debe contener huespedes, check-in, check-out, tarifa, extras, descuentos, deposito, notas y origen manual.
- `RSV-03`: el precio debe calcularse a partir de noches y tarifa base, permitiendo un total acordado editable antes de confirmar.
- `RSV-04`: los estados deben ser borrador, confirmada, check-in, check-out, cancelada y no presentada.
- `RSV-05`: confirmar debe volver a validar disponibilidad dentro de una transaccion.
- `RSV-06`: un bloqueo debe reservar fechas sin crear huesped ni ingreso.
- `RSV-07`: confirmar una reserva debe generar sus cargos sin duplicados.
- `RSV-08`: cancelar debe liberar fechas, conservar historia, revertir cargos no ganados y permitir definir manualmente penalidad, importe retenido, reembolso o saldo pendiente.
- `RSV-09`: V1 no debe importar ni exportar disponibilidad a plataformas externas.

### 8.9 Cargos, pagos y recibos

- `FIN-01`: un cargo debe identificar parte deudora, unidad, concepto, `recognitionDate`, periodo de servicio opcional, emision, vencimiento, importe y origen.
- `FIN-01A`: el ciclo persistido de un cargo debe ser borrador, emitido o anulado; abierto, parcial, pagado y vencido se calculan desde saldo y fechas.
- `FIN-02`: los conceptos pueden ser alquiler, mora, servicio, gasto trasladado, reserva u otra categoria configurable.
- `FIN-03`: un pago externo manual debe registrar parte, fecha efectiva de recepcion, medio, importe, referencia, observacion y comprobante opcional.
- `FIN-04`: los medios iniciales deben incluir efectivo, transferencia y otro; la organizacion puede ampliarlos.
- `FIN-05`: un pago puede aplicarse total o parcialmente a uno o varios cargos de la misma organizacion y parte deudora.
- `FIN-06`: la suma de aplicaciones activas y reembolsos confirmados no puede superar el importe del pago; una aplicacion tampoco puede superar el saldo del cargo.
- `FIN-07`: el importe del pago menos aplicaciones activas y reembolsos confirmados permanece como saldo a favor no aplicado.
- `FIN-08`: confirmar un pago externo debe generar un numero secuencial unico y un recibo interno no fiscal.
- `FIN-09`: anular corrige un registro erroneo sin movimiento real; si el dinero fue recibido y luego devuelto, debe usarse un reembolso. Ambos conservan recibo, motivo e historia.
- `FIN-10`: el sistema debe admitir numero, timbrado, fecha y archivo de una factura externa sin emitirla ni validarla fiscalmente.
- `FIN-11`: los periodos financieros pueden cerrarse; reabrir exige permiso especial, motivo y auditoria.
- `FIN-12`: un pago externo debe pasar de borrador a confirmado o anulado; su importe y fecha de recepcion quedan fijos al confirmar. Una fuente `DEPOSIT_APPLICATION` se crea confirmada y marcada como no monetaria.
- `FIN-13`: una aplicacion debe guardar `appliedAt`, que no puede ser anterior a la fecha de disponibilidad de su fuente y determina su periodo de atribucion a unidad/propietario.
- `FIN-14`: si el pago se aplica al confirmarlo, `appliedAt` coincide con la fecha de recepcion; una aplicacion posterior pertenece al periodo en que se confirma.
- `FIN-15`: revertir una aplicacion crea una reversion negativa fechada; no elimina ni retrofecha la aplicacion original. Si ya fue liquidada, la reversion se incluye como ajuste en la siguiente liquidacion abierta.
- `FIN-16`: la entrada de caja se informa por fecha de recepcion del pago, mientras el cobro atribuible se informa por `appliedAt`; ambas metricas deben permanecer separadas.
- `FIN-17`: una aplicacion incluida en una liquidacion pagada solo se corrige mediante una reversion/ajuste fechado en un periodo abierto; la liquidacion pagada permanece intacta.
- `FIN-18`: el primer movimiento de un mes crea automaticamente su periodo abierto si todavia no existe.
- `FIN-19`: un reembolso debe referenciar un pago externo confirmado y registrar `refundedAt`, importe, medio, referencia, motivo y comprobante opcional.
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
- `DEP-06`: la aplicacion del deposito se considera cobro atribuible y puede entrar en la liquidacion del propietario por su `appliedAt`.
- `DEP-07`: una retencion por dano, deuda o cancelacion debe representarse con un cargo justificado y la aplicacion del deposito a ese cargo.
- `DEP-08`: una devolucion reduce fondos retenidos y se muestra como salida de caja no operativa, no como gasto.
- `DEP-09`: anular o corregir un movimiento crea trazabilidad y no cambia silenciosamente movimientos anteriores.

### 8.11 Gastos

- `EXP-01`: un gasto debe pertenecer inicialmente a una unidad o una ubicacion.
- `EXP-02`: debe admitir categoria configurable, proveedor opcional, fecha, descripcion general, estado, comprobantes y fecha de pago.
- `EXP-03`: debe admitir una o varias lineas de detalle con descripcion e importe.
- `EXP-04`: la suma de lineas debe coincidir exactamente con el total del gasto.
- `EXP-05`: un gasto puede quedar planificado, pendiente de aprobacion, aprobado, incurrido, pagado o anulado.
- `EXP-05A`: al pasar a incurrido debe fijar `incurredAt`; al pasar a pagado debe fijar `paidAt` y conservar `incurredAt` para el criterio devengado.
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
- `MNT-02`: los estados deben ser abierta, en evaluacion, pendiente de aprobacion, aprobada, en curso, resuelta, cerrada y cancelada.
- `MNT-03`: una incidencia puede agrupar estimaciones, aprobaciones y gastos reales.
- `MNT-04`: organizacion, ubicaciones y unidades pueden definir monto minimo y uno o varios propietarios requeridos; prevalece unidad, luego ubicacion y finalmente organizacion.
- `MNT-05`: una aprobacion se completa cuando todos los aprobadores configurados aceptan; un rechazo devuelve el caso a evaluacion.
- `MNT-06`: una emergencia puede omitir aprobacion previa solamente con permiso, motivo y evidencia.
- `MNT-07`: propietarios y equipo deben recibir avisos de solicitud, decision y cambio relevante de estado.
- `MNT-08`: un gasto sin imputacion de unidad usa la politica de ubicacion; un gasto imputado a unidades combina el conjunto de aprobadores requeridos de esas unidades sin duplicarlos.
- `MNT-09`: la solicitud de aprobacion congela una version de monto, lineas, alcance, imputacion y documentos de presupuesto.
- `MNT-10`: un gasto real menor o igual al monto aprobado puede continuar; cualquier aumento o cambio de alcance exige una nueva aprobacion, salvo emergencia justificada.

### 8.13 Liquidaciones a propietarios

- `LIQ-01`: una liquidacion debe pertenecer a un propietario y a un periodo financiero mensual cerrado.
- `LIQ-02`: se calcula con atribucion de caja: aplicaciones confirmadas por `appliedAt` menos gastos pagados por `paidAt`, ambos atribuibles al propietario.
- `LIQ-03`: la participacion de los cobros procede de la instantanea del cargo; la de gastos procede de su imputacion e instantanea.
- `LIQ-04`: cobros no aplicados, depositos retenidos y gastos sin atribuir se muestran como informativos y no integran el neto liquidable.
- `LIQ-05`: V1 no descuenta comision automatica de administradora.
- `LIQ-06`: un honorario excepcional puede cargarse manualmente como gasto detallado y auditable.
- `LIQ-07`: la vista previa debe permitir detectar movimientos sin imputar antes de confirmar.
- `LIQ-08`: confirmar crea una instantanea inmutable con sus lineas y totales.
- `LIQ-09`: la liquidacion puede marcarse pagada con fecha, medio, referencia y comprobante; esto crea una salida `OwnerDisbursement` y no un gasto.
- `LIQ-10`: anular o reabrir exige permiso, motivo y auditoria; nunca sobrescribe la instantanea anterior.
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
- `DOC-07`: el metadato debe incluir organizacion, entidad propietaria, nombre original, tipo, tamano, checksum y autor.
- `DOC-08`: un archivo referenciado se archiva o versiona; no se reemplaza silenciosamente.
- `DOC-09`: cada documento debe declarar audiencia: solo equipo, propietarios afectados o partes seleccionadas.
- `DOC-10`: el backend debe validar audiencia y vigencia de titularidad antes de emitir una URL firmada.

### 8.15 Notificaciones

- `NTF-01`: email se envia mediante Resend.
- `NTF-02`: WhatsApp se entrega a un webhook HTTPS de despliegue mediante `POST` firmado; el bridge externo traduce el mensaje al proveedor elegido.
- `NTF-03`: las plantillas deben ser configurables por organizacion y canal, con variables controladas.
- `NTF-04`: los eventos iniciales incluyen vencimiento proximo, mora, contrato por finalizar, reserva confirmada, recordatorio de estadia, aprobacion de gasto, incidencia y liquidacion disponible.
- `NTF-05`: cada envio debe registrar destinatario, consentimiento o habilitacion del canal, plantilla, estado, intentos, respuesta del proveedor y fecha.
- `NTF-06`: los estados deben ser pendiente, procesando, enviado, entregado cuando el proveedor lo informe, fallido y cancelado.
- `NTF-07`: un fallo debe reintentarse con espera creciente y limite configurable; despues debe quedar visible para reenvio manual.
- `NTF-08`: fallar un mensaje no debe revertir un pago, reserva, gasto o liquidacion ya confirmados.
- `NTF-09`: el webhook debe recibir identificador, destinatario, plantilla, variables y texto renderizado, y aceptar callbacks firmados de estado asociados al mismo identificador.
- `NTF-10`: si no hay webhook configurado, el canal WhatsApp se muestra deshabilitado y no se encolan mensajes que aparenten haber sido enviados.
- `NTF-11`: V1 debe probar el contrato del webhook con un receptor HTTP controlado; la seleccion y operacion del bridge de produccion no forman parte del nucleo.

### 8.16 Importacion

- `IMP-01`: el usuario puede cargar ubicaciones, unidades y partes mediante formularios.
- `IMP-02`: debe existir una plantilla CSV separada para ubicaciones, unidades y partes.
- `IMP-03`: la importacion debe validar estructura, datos, duplicados y referencias antes de confirmar.
- `IMP-04`: la vista previa debe indicar filas validas y errores con numero de fila y campo.
- `IMP-05`: el usuario debe corregir los errores o excluir filas invalidas de forma explicita antes de importar.
- `IMP-06`: los contratos y movimientos iniciales se cargan manualmente en V1.

### 8.17 Auditoria

- `AUD-01`: deben auditarse accesos administrativos, cambios de permisos, titularidades, modalidades, contratos, reservas, movimientos, periodos, aprobaciones y documentos sensibles.
- `AUD-02`: el evento debe incluir organizacion, actor, accion, entidad, fecha, correlacion y cambios relevantes antes/despues.
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
| Ingreso devengado | Cargos emitidos cuya `recognitionDate` cae dentro del rango, menos anulaciones y ajustes con la misma regla. El importe no se prorratea por interseccion. |
| Entrada de caja | Pagos externos confirmados por fecha efectiva de recepcion, mas recepciones de deposito; no implica atribucion a unidad o propietario. |
| Cobrado aplicado | Aplicaciones confirmadas por `appliedAt`, incluidas aplicaciones de deposito, menos reversiones efectivas del rango. |
| Cobro no aplicado | Pagos externos recibidos hasta la fecha de corte menos aplicaciones activas y reembolsos confirmados hasta esa fecha; no se atribuye a unidad o propietario. |
| Saldo pendiente | Total vigente de cargos menos aplicaciones y ajustes confirmados hasta la fecha de corte. |
| Gasto devengado | Gastos confirmados por `incurredAt`, atribuidos o sin atribuir segun el reporte. Un gasto pagado sigue formando parte del devengado original. |
| Gasto de caja | Gastos confirmados por `paidAt` dentro del rango. |
| Fondos retenidos | Saldo acumulado de depositos recibidos menos aplicaciones y devoluciones hasta la fecha de corte. |
| Resultado devengado | Ingreso devengado menos gasto devengado, sin incluir depositos. |
| Resultado cobrado atribuible | Cobrado aplicado menos gasto de caja atribuible; no es igual a entrada bancaria cuando existen cobros sin aplicar o depositos. |
| Reembolsos externos | Devoluciones confirmadas por `refundedAt`; reducen caja, pero no se registran como gasto. |
| Flujo de caja registrado | Pagos externos y depositos recibidos menos reembolsos, gastos pagados, depositos devueltos y liquidaciones pagadas; las aplicaciones internas no vuelven a mover caja. |
| Ocupacion | Noches o dias ocupables cubiertos por contrato/reserva frente al total disponible del rango. |

Una aplicacion creada despues del pago no mueve la entrada de caja original. Se atribuye a unidad y propietario en `appliedAt`. Por eso un reporte puede mostrar entrada de caja en agosto y cobro aplicado en septiembre sin contar dos veces el dinero.

Un cargo cuyo servicio va del 20 de agosto al 19 de septiembre se reconoce completo en agosto si `recognitionDate` es 20 de agosto. El reporte de ocupacion si distribuye los dias por interseccion, pero el financiero no prorratea ese cargo.

### 9.3 Reportes obligatorios

| Reporte | Regla temporal | Filtros minimos | Salida y agrupacion minima |
| --- | --- | --- | --- |
| Resumen ejecutivo | Rango; muestra devengado, entrada, aplicacion y caja con sus fechas propias. | Propietario, ubicacion, unidad. | Sin filtro patrimonial muestra cargos, entrada, reembolsos, aplicado, deuda, gastos, depositos y flujo; con filtro patrimonial sustituye entrada/flujo global por importes aplicados y atribuibles. |
| Matriz mensual por unidad | Mes de servicio para devengado; `appliedAt` y `paidAt` para atribucion de caja. | Propietario, ubicacion, modalidad, estado operativo. | Una fila por unidad activa en el mes con ocupacion, devengado, cobrado aplicado, pendiente, gasto devengado y pagado; entradas no aplicadas aparecen en un resumen separado. |
| Ingresos y egresos | Rango y criterio elegido; siempre identifica la fecha usada. | Propietario, ubicacion, unidad, categoria. | A nivel organizacion incluye entradas/reembolsos; con dimension patrimonial usa aplicaciones y gastos atribuibles, agrupables por dia, mes, categoria y alcance. |
| Estado de cuenta de parte | Cargos por periodo y aplicaciones por `appliedAt`, con fecha de corte inclusiva. | Parte, unidad, contrato o reserva. | Cronologia de cargos, aplicaciones, reversiones, saldo a favor y deuda acumulada. |
| Morosidad | Saldo existente al cierre de la fecha de corte. | Propietario, ubicacion, unidad, parte. | Cargo, vencimiento, saldo y tramos 1-30, 31-60, 61-90 y mas de 90 dias. |
| Ocupacion y vacancia | Interseccion de contrato/reserva/bloqueo con el rango. | Propietario, ubicacion, unidad, modalidad. | Dias o noches disponibles, ocupados, bloqueados y porcentaje por unidad y ubicacion. |
| Reservas temporarias | Estadias por check-in/check-out; finanzas por fecha de cargo, aplicacion o pago. | Ubicacion, unidad, huesped, estado. | Estadias, noches, tarifa, cargos, cobrado aplicado, saldo, cancelaciones y ocupacion. |
| Contratos | Estado a una fecha de corte o eventos dentro de un rango. | Propietario, ubicacion, unidad, modalidad, estado. | Partes, vigencia, canon aplicable, proximo vencimiento, deuda y deposito. |
| Gastos | `incurredAt` para devengado o `paidAt` para caja. | Propietario, ubicacion, unidad, categoria, proveedor, aprobacion. | Lineas, total, estado, imputacion, atribucion, cargo trasladado y agrupaciones por categoria/alcance. |
| Depositos | Movimientos por su fecha efectiva y saldo a fecha de corte. | Ubicacion, unidad, parte, contrato/reserva, estado. | Acordado, recibido, retenido, aplicado, devuelto y referencias de cargos. |
| Liquidaciones | Periodo financiero mensual. | Propietario, estado, ubicacion de origen. | Lineas fuente, cobrado aplicado, gastos pagados, ajustes, informativos, neto y revision. |
| Sin aplicar o imputar | Existencia a fecha de corte. | Tipo de movimiento, propietario, ubicacion, unidad, antiguedad. | Cobros no aplicados, gastos sin imputar/atribuir y motivo de exclusion de liquidaciones. |
| Auditoria | Fecha/hora del evento dentro del rango. | Actor, accion, entidad. | Cronologia, correlacion y cambios autorizados, respetando ocultamiento de secretos. |

La fecha final de un filtro civil es inclusiva en la zona horaria de la organizacion. Cada reporte debe mostrar la regla temporal aplicada y la fecha de corte para evitar interpretar una aplicacion como si fuera la recepcion original del pago.

### 9.4 Reglas de presentacion

- Una unidad activa debe aparecer en la matriz del periodo aunque este desocupada y tenga ingresos cero.
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
4. El sistema calcula aplicaciones por `appliedAt`, gastos por `paidAt` y movimientos informativos no liquidables.
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
- La transaccion de negocio guarda tanto el cambio como un evento de salida.
- El worker reclama trabajos con bloqueo seguro, actualiza intentos y evita procesamiento concurrente duplicado.
- Los trabajos incluyen generacion de cargos, mora automatica, avisos, PDF y limpieza de artefactos temporales.
- Un trabajo debe declarar clave de idempotencia, cantidad maxima de intentos y politica de reintento.
- Los fallos agotados quedan visibles para diagnostico y reejecucion autorizada.

### 12.8 Archivos

- La API autoriza cada carga y descarga.
- Los objetos usan claves no predecibles con prefijo logico por organizacion.
- Spaces permanece privado; no se guardan URL publicas permanentes.
- El checksum permite detectar cargas repetidas o corruptas.
- Los metadatos permanecen en PostgreSQL y el contenido binario en Spaces.

## 13. API y flujo de datos

### 13.1 API REST

- Prefijo inicial `/api/v1`.
- OpenAPI es parte del contrato entregable.
- Las entradas y salidas usan esquemas Zod estables.
- Listados usan paginacion, orden y filtros explicitos.
- Mutaciones sensibles aceptan clave de idempotencia.
- Los recursos nunca confian en un `organizationId` enviado por el cliente para autorizar acceso.
- Cambios incompatibles requieren una nueva version de API.

### 13.2 Flujo de una mutacion

1. Next.js envia la solicitud autenticada.
2. NestJS asigna identificador de correlacion.
3. La capa de identidad resuelve usuario, membresia y organizacion.
4. Zod valida estructura y tipos.
5. La autorizacion verifica permiso y alcance de datos.
6. El modulo de dominio valida reglas de negocio.
7. Una transaccion guarda datos, auditoria y eventos de salida.
8. La API responde con el estado confirmado.
9. El worker procesa efectos secundarios sin reabrir la transaccion original.

### 13.3 Flujo de reporte

1. El usuario define filtros y criterio financiero.
2. La API valida alcance y ejecuta una consulta de lectura consistente.
3. La pantalla recibe datos y metadatos de filtros.
4. Si se solicita PDF, se guarda una solicitud con los mismos filtros normalizados.
5. El worker genera el PDF, lo almacena en Spaces y notifica disponibilidad.
6. La descarga vuelve a verificar autorizacion.

## 14. Seguridad

### 14.1 Autenticacion y sesion

- Contrasenas con hash resistente y parametros revisables.
- Cookies de sesion `HttpOnly`, `Secure` y `SameSite` apropiado.
- Proteccion CSRF u origen estricto para solicitudes que modifican datos.
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
  "code": "BOOKING_OVERLAP",
  "message": "La unidad ya tiene una reserva o bloqueo para esas fechas.",
  "fieldErrors": {
    "checkIn": ["El intervalo entra en conflicto con una reserva confirmada."]
  },
  "correlationId": "identificador-seguro"
}
```

- `400` para solicitud mal formada.
- `401` para sesion ausente o invalida.
- `403` para permiso o alcance insuficiente.
- `404` para recurso inexistente dentro del alcance autorizado.
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

### 16.2 Disponibilidad operativa

- Health checks separados para web, API, worker, base y dependencias externas.
- Degradacion controlada: una caida de notificaciones no impide registrar cobros o gastos.
- Los trabajos pendientes sobreviven reinicios del worker.
- Las operaciones criticas usan transacciones y claves de idempotencia.

### 16.3 Respaldo y recuperacion

- Respaldo cifrado diario de PostgreSQL con retencion minima de 30 dias.
- Versionado o politica de recuperacion equivalente para archivos necesarios.
- Prueba documentada de restauracion al menos una vez por trimestre.
- La restauracion debe incluir verificacion de integridad entre metadatos y objetos.

### 16.4 Observabilidad

- Logs estructurados con servicio, organizacion anonimizada cuando corresponda, usuario, ruta y correlacion.
- Metricas de latencia, errores, conexiones, trabajos, reintentos y proveedores externos.
- Alertas para errores sostenidos, cola detenida, respaldos fallidos y almacenamiento no disponible.
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
- Reserva, bloqueo, check-in, cancelacion y reembolso manual.
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
- Una cancelacion libera fechas y conserva retenciones/reembolsos manuales.
- La retencion se aplica a un cargo de penalidad y el resto se reembolsa desde saldo externo no aplicado.
- Un bloqueo evita reservas sin generar ingresos.

### 18.6 Copropiedad y liquidacion

- Una unidad con dos propietarios exige participaciones que sumen 100 %.
- Cambiar porcentajes en septiembre no modifica cargos o liquidaciones de agosto.
- Un cargo mensual cuyo servicio inicia antes de un cambio de propietario conserva las participaciones vigentes al inicio; V1 no lo prorratea automaticamente.
- La liquidacion usa aplicaciones por `appliedAt` y gastos por `paidAt`, sin volver a incluir una fuente ya liquidada.
- Depositos y cobros no aplicados se informan, pero no aumentan el neto liquidable.
- Confirmar la liquidacion congela sus lineas y genera el mismo total en PDF.
- Una liquidacion pagada no cambia al registrar una correccion tardia; el ajuste aparece enlazado en el siguiente periodo abierto.

### 18.7 Depositos y fechas de caja

- Recibir un deposito aumenta entrada de caja y fondos retenidos, pero no ingreso.
- Aplicar parte del deposito a un cargo reduce el saldo retenido, cancela deuda y no crea una nueva entrada de caja.
- Devolver el deposito se muestra como salida de caja no operativa y no como gasto.
- Un pago recibido en agosto y aplicado en septiembre aparece como entrada en agosto y como cobro aplicado en septiembre, sin duplicarse.
- Un reembolso de septiembre por un pago de agosto aparece como salida en septiembre y no reescribe la entrada de agosto.
- Si un pago se aplica parcialmente y se reembolsa todo el remanente, su cobro no aplicado queda en cero y la aplicacion conserva su saldo correcto.

### 18.8 Aprobacion y traslado de gastos

- Un gasto que supera el umbral solicita a los aprobadores configurados.
- Un propietario puede aprobar o rechazar desde su portal.
- Una emergencia exige permiso, motivo y evidencia si omite aprobacion.
- Un gasto trasladado al inquilino genera un cargo enlazado por el importe elegido y no se recupera dos veces.
- Aumentar el total o cambiar unidades/imputacion despues de aprobar invalida la aprobacion y exige una nueva version.

### 18.9 Cierre de periodos

- Cerrar agosto impide retrofechar cargos, pagos, aplicaciones, gastos o depositos dentro de agosto.
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
| Alteracion de historia financiera | Anulaciones auditadas, instantaneas y prohibicion de borrado de confirmados. |
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
| 0. Plataforma segura | Monorepo, configuracion, PostgreSQL local, autenticacion, organizaciones, membresias, permisos, aislamiento, auditoria base, API y worker base. | Ninguna. | Dos organizaciones operan sin acceso cruzado; API, migraciones y cola persistida tienen pruebas de integracion. |
| 1. Cartera | Partes, ubicaciones, unidades, nombres sugeridos, tipos, modalidades, venta, titularidades, portal propietario minimo e importacion CSV basica. | Incremento 0. | Se reproduce U1 con diez unidades, modalidades mixtas, copropiedad e historia sin inconsistencias. |
| 2. Alquiler tradicional y finanzas | Contratos, cronogramas, cargos, mora, pagos, aplicaciones, recibos, depositos, periodos y reportes financieros base. | Incremento 1. | Cargo idempotente, pago parcial, fechas de caja/aplicacion, deposito y cierre mensual cuadran bajo concurrencia. |
| 3. Gastos y propietarios | Incidencias, aprobaciones versionadas, gastos, imputaciones, traslado al inquilino, liquidaciones y portal completo de propietario. | Incremento 2. | Casos D1/D2, gasto de porton, copropiedad y liquidacion producen totales trazables en pantalla. |
| 4. Alquiler temporario | Calendario, bloqueos, reservas, tarifas, cargos, check-in/out, cancelacion y uso de depositos. | Incrementos 1 y 2. | Reservas concurrentes no se superponen y cancelaciones concilian cargos, depositos y fechas. |
| 5. Documentos, comunicaciones y endurecimiento | Plantillas/PDF, Spaces, Resend, webhook WhatsApp, reportes completos, observabilidad, rendimiento, accesibilidad, respaldo y restauracion. | Incrementos 0 a 4. | Todos los criterios de V1, PDF/pantalla, rendimiento, seguridad y restauracion pasan de extremo a extremo. |

La trazabilidad minima entre requisitos e incrementos es:

- Incremento 0: `ORG`, `IAM`, base de `AUD`, secciones 12 a 15.
- Incremento 1: `PTY`, `PRT`, `OWN`, `IMP` y visibilidad patrimonial basica.
- Incremento 2: `CTR`, `MOR`, `FIN`, `DEP`, periodos financieros y reportes base de deuda/caja.
- Incremento 3: `EXP`, `MNT`, `LIQ`, portal financiero de propietario y caso mensual D1/D2.
- Incremento 4: `RSV` y sus integraciones con cargos, pagos, depositos y disponibilidad.
- Incremento 5: `DOC`, `NTF`, todos los reportes restantes y requisitos no funcionales finales.

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
- No existen defectos conocidos que puedan perder dinero, duplicar reservas, filtrar datos o alterar historia.

Este documento define el producto, sus reglas y los limites de cada entrega. Las tareas tecnicas se planificaran despues de la revision final, un incremento por vez y comenzando por el incremento 0.
