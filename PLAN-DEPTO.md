# PLAN-DEPTO

Especificacion funcional y tecnica para la primera version de un sistema SaaS de administracion de alquileres.

| Dato | Valor |
| --- | --- |
| Estado | Revision final de casos frontera incorporada |
| Fecha | 2026-08-09 |
| Version objetivo | V1 web adaptable |
| Mercado inicial | Paraguay |
| Idioma inicial | Espanol (`es-PY`) |
| Moneda | Guarani paraguayo (`PYG`) |
| Zona horaria de V1 | `America/Asuncion`, unica y no configurable por organizacion |
| Modelo | SaaS multiempresa |
| Arquitectura | Monolito modular con API y worker separados |

## 1. Resumen ejecutivo

PLAN-DEPTO sera un sistema para que propietarios individuales y empresas administradoras controlen, desde una fuente confiable, ubicaciones, unidades, contratos, alojamiento temporario, eventos, pases diarios, cobros, gastos, incidencias y liquidaciones.

Una ubicacion contendra una o muchas unidades. Cada unidad tendra nombre editable, tipo fisico, estado administrativo manual y estado operativo derivado. Podra habilitar simultaneamente las modalidades tradicional, comercial, alojamiento temporario y eventos mediante vigencias independientes. Una matriz simetrica por unidad decidira que modalidades distintas pueden coincidir; toda combinacion no autorizada se denegara.

Los contratos tradicionales y comerciales seran finitos, tendran firma y vigencia separadas, ciclos configurables, ocurrencias futuras materializadas, adendas y cierre administrativo de cuotas. Alojamiento y eventos seran reservas distintas: el primero operara por noches y el segundo por fecha-hora, paquetes y aforo. Los pases diarios perteneceran a una ubicacion, consumiran cupo propio por franja y no ocuparan unidades.

El nucleo financiero registrara exclusivamente fondos administrados por la organizacion. Diferenciara cargos, entrada de caja, cobro aplicado, deuda, gasto incurrido, gasto pagado, devoluciones de proveedor, garantias y desembolsos. Cada contrato o reserva identificada tendra una unica parte de facturacion, separada del pagador real.

V1 sera una aplicacion web adaptable, operara solo en PYG y `America/Asuncion`, y expondra una API REST versionada para una futura aplicacion movil.

## 2. Objetivos

### 2.1 Objetivos principales

- Centralizar ubicaciones, unidades, partes, contratos, alojamiento, eventos, pases, documentos y movimientos.
- Saber mes a mes cuanto se genero, cuanto se cobro, cuanto sigue pendiente y cuanto se gasto.
- Mostrar resultados por organizacion, propietario, ubicacion, unidad y rango de fechas.
- Mantener visibles las unidades desocupadas con ingreso cero en los reportes del periodo.
- Permitir modalidades simultaneas sin aceptar compromisos incompatibles.
- Evitar superposiciones, sobreventa de cupos y cargos periodicos duplicados.
- Preservar un historial auditable de modalidades, compatibilidad, titularidad, contratos, precios y finanzas.
- Permitir que los propietarios consulten su cartera, descarguen documentos y aprueben gastos.
- Aislar completamente los datos de cada organizacion SaaS.
- Mantener separados el estado administrativo manual y la operacion derivada del calendario.

### 2.2 Criterios de exito de V1

- Todo movimiento financiero confirmado tiene origen, responsable, fecha, detalle e historial de correcciones.
- Los totales visibles en pantalla coinciden con los PDF generados con los mismos filtros.
- Un reporte puede explicar la diferencia entre ingreso devengado, entrada de caja, cobro aplicado, deuda y resultado atribuible.
- Una reejecucion de procesos automaticos no duplica cargos, recordatorios ni documentos.
- Dos confirmaciones concurrentes no crean compromisos incompatibles ni exceden un cupo.
- Toda distribucion de titularidad activa suma exactamente `100.0000 %`.
- Ningun periodo financiero se cierra con cuotas contractuales administrativamente abiertas.
- Ningun usuario puede consultar o modificar datos de otra organizacion.
- Los flujos principales funcionan correctamente desde 360 px de ancho y en escritorio.

## 3. Alcance de V1

### 3.1 Incluido

- SaaS multiempresa para propietarios individuales y administradoras.
- Alta de organizaciones por superadministrador y por autorregistro con email verificado.
- Usuarios internos con roles y permisos configurables.
- Portal de propietarios con modo separado del equipo, representantes muchos-a-muchos, consulta, descarga y aprobacion.
- Ubicaciones, unidades, tipos fisicos configurables y nombres editables.
- Estado administrativo manual y estado operativo derivado por fecha o intervalo.
- Copropiedad mediante distribuciones atomicas, porcentajes de cuatro decimales y vigencias semiabiertas.
- Modalidades tradicional, comercial, alojamiento temporario y eventos con vigencias independientes y simultaneas.
- Matriz simetrica de compatibilidad por unidad, con denegacion por defecto.
- Marca de unidad en venta, compatible con alquileres activos.
- Contratos tradicionales y comerciales finitos, uno por unidad en cada intervalo incompatible.
- Firma y vigencia separadas, ciclos configurables, ocurrencias futuras, adendas y terminacion efectiva.
- Cierre administrativo de cuotas contractuales antes del cierre financiero.
- Mora manual o automatica segun configuracion.
- Calendario comun por unidad, bloqueos y buffers.
- Reservas de alojamiento por noches con tarifas por noche, feriados configurables y horarios de check-in/out.
- Reservas de eventos por fecha-hora, paquetes, asistentes, aforo estricto y buffers.
- Pases diarios de ubicacion con categorias, tarifas, cupo por franja y pago total obligatorio.
- Cargos, pagos manuales, aplicaciones de pago, saldos y recibos internos.
- Registro de facturas externas sin emision fiscal.
- Anticipos y garantias explicitamente diferenciados; garantias como fondos retenidos.
- Incidencias, aprobaciones de propietario y gastos con detalle.
- Gastos de unidad y ubicacion, con imputacion opcional.
- Traslado total o parcial de un gasto al inquilino.
- Liquidaciones a propietarios sin comision automatica de administradora.
- Documentos generados desde plantillas y archivos adjuntos para usuarios autenticados.
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
- Zonas horarias distintas de `America/Asuncion`.
- Facturacion y cobro recurrente de la suscripcion SaaS.
- Importacion masiva de contratos y movimientos historicos.
- Gestion avanzada de inventario, ordenes de compra o mantenimiento preventivo.
- Portal de inquilinos, huespedes, responsables de eventos, compradores de pases, garantes o proveedores.
- Entrega o descarga de documentos por partes sin una cuenta autenticada.
- Campanas promocionales o marketing.
- Integracion directa con una API especifica de WhatsApp; V1 entrega un webhook generico para conectar un bridge externo.

## 4. Actores y acceso

### 4.1 Superadministrador de plataforma

- Crea organizaciones y su primer administrador.
- Consulta y cambia el estado operativo de una organizacion.
- Puede suspender y reactivar una organizacion conservando sus datos.
- Puede enviar una invitacion fija de recuperacion administrativa sin suplantar al destinatario.
- Puede consultar siempre la auditoria organizacional ya limitada y enmascarada al persistirse.
- Esa excepcion no concede acceso a propiedades, contratos, finanzas, reportes, documentos, archivos ni endpoints de negocio.
- Para acceder a datos de negocio debe ser invitado como miembro; esa incorporacion queda auditada.
- Gestiona la operacion SaaS, pero no suscripciones ni cobros de planes en V1.

### 4.2 Administrador de organizacion

- Configura identidad, catalogos, feriados, horarios, buffers, documentos, avisos y reglas de negocio.
- Invita usuarios y crea roles a partir de permisos disponibles.
- Administra representantes de partes propietarias y matrices de compatibilidad por unidad.
- Controla las acciones de cada rol y las politicas de aprobacion.
- Puede cerrar y reabrir cuotas y periodos con permiso especial y motivo obligatorio.
- No puede cambiar PYG ni `America/Asuncion` en V1.

### 4.3 Miembro del equipo

- Accede solamente a las acciones habilitadas por sus roles.
- Los permisos se definen por accion, por ejemplo ver, crear, editar, confirmar, anular, aprobar, cerrar, exportar o administrar.
- La organizacion recibe plantillas iniciales de roles, pero puede crear y modificar sus propios roles.
- En V1 los miembros internos autorizados tienen alcance sobre toda la organizacion; no existen restricciones por ubicacion o unidad.
- Identidad, permisos y organizacion activa son controles separados: tener permiso para ver gastos nunca elimina el filtro de organizacion.
- Los roles son aditivos; un usuario no puede conceder permisos que no posee ni dejar a la organizacion sin administrador.
- Si tambien representa a un propietario, debe elegir explicitamente modo equipo o modo propietario; los permisos no se unen.

### 4.4 Propietario y representante

- La parte propietaria es titular; uno o varios usuarios acceden mediante grants de representacion vigentes.
- Un representante nuevo ve todo el historial elegible de la parte, aunque sea anterior al grant.
- Mientras la titularidad esta vigente, ve la unidad y los registros autorizados que intersectan su vigencia.
- Al terminar la titularidad, conserva liquidaciones, movimientos atribuidos y documentos historicos dirigidos a la parte, pero no operacion posterior.
- La vista contractual es un resumen minimizado sin identificaciones, contactos, garantes, comprobantes ni adjuntos privados del inquilino.
- Los importes se muestran segun participacion historica y no revelan liquidaciones de otros copropietarios.
- Una parte propietaria emite un solo voto por solicitud, aunque tenga varios representantes.
- Descarga reportes y documentos solo despues de autenticacion y autorizacion.
- No modifica unidades, contratos ni movimientos en V1.

### 4.5 Otras partes y ventas anonimas

- Inquilinos, huespedes, responsables de eventos, garantes, proveedores y compradores se registran como partes cuando corresponde, pero no inician sesion en V1.
- Pueden recibir notificaciones operativas en canales consentidos, pero no documentos ni enlaces de descarga.
- Una venta anonima de pase diario puede omitir comprador y responsable.

## 5. Glosario del dominio

| Termino | Definicion |
| --- | --- |
| Organizacion | Limite SaaS de un cliente. V1 usa PYG y `America/Asuncion`. |
| Ubicacion | Edificio, complejo, terreno o direccion que agrupa unidades y configura pases diarios. |
| Unidad | Bien individual operable, por ejemplo departamento, casa, duplex, cabana o salon. |
| Tipo fisico | Clasificacion configurable que no determina la forma de comercializacion. |
| Modalidad | Capacidad comercial habilitada: tradicional, comercial, alojamiento temporario o eventos. |
| Vigencia de modalidad | Intervalo semiabierto en que una modalidad esta habilitada; modalidades distintas pueden coexistir. |
| Matriz de compatibilidad | Regla simetrica por unidad para autorizar coincidencias entre modalidades distintas; la ausencia deniega. |
| Estado administrativo | Estado manual de gestion, mostrado separado del calendario. |
| Estado operativo | Disponibilidad, ocupacion o bloqueo derivados para una fecha o intervalo. |
| Compromiso de calendario | Contrato, reserva de alojamiento, reserva de evento o bloqueo que ocupa un intervalo. |
| Parte | Persona fisica o juridica local a una organizacion y capaz de asumir roles de negocio. |
| Parte de facturacion | Unica parte deudora de los cargos de un contrato o reserva identificada. |
| Pagador real | Parte que entrega fondos; puede diferir de la parte de facturacion. |
| Grant de representante | Acceso muchos-a-muchos entre un usuario y una parte propietaria. |
| Distribucion de titularidad | Version atomica de participaciones para una vigencia; suma `100.0000 %`. |
| Titularidad | Linea de una distribucion que asigna porcentaje a una parte propietaria. |
| Contrato | Acuerdo tradicional o comercial finito, asociado a una unidad y parte de facturacion. |
| Fecha de firma | `signedOn`; fecha opcional e independiente de la vigencia contractual. |
| Fin pactado | `agreedEndsOn`; ultimo dia contractual inclusivo, conservado aunque haya terminacion anticipada. |
| Terminacion efectiva | `terminatedOn`; ultimo dia efectivo inclusivo que acorta la operacion sin sobrescribir el fin pactado. |
| Ciclo contractual | Regla por mes calendario o ancla aniversario que divide la vigencia. |
| Cuota contractual | Ocurrencia materializada con ciclo de vida y cierre administrativo independientes. |
| Cierre de cuota | Bloqueo administrativo de importe y detalle; no paga, condona ni detiene deuda o mora. |
| Adenda | Cambio contractual versionado con fecha efectiva, motivo y documento opcional. |
| Reserva de alojamiento | Estadia por noches con horarios programados y lineas tarifarias por noche. |
| Reserva de evento | Alquiler por fecha-hora, paquete, asistentes, aforo y buffers. |
| Buffer | Tiempo de preparacion que bloquea disponibilidad sin aumentar el precio salvo cargo explicito. |
| Pase diario | Acceso a una ubicacion por franja y cantidades por categoria; no ocupa una unidad. |
| Senia | Monto inicial que debe clasificarse como anticipo de precio o garantia. |
| Cargo | Importe exigible por alquiler, mora, servicio, reserva, pase, gasto trasladado u otro concepto. |
| Pago | Fuente administrada confirmada que registra parte de facturacion y pagador real. |
| Aplicacion de pago | Parte de un pago asignada a un cargo concreto. |
| Reversion de aplicacion | Contramovimiento parcial o total, inmutable y enlazado. |
| Reembolso de pago | Salida real que devuelve saldo externo no aplicado; no es gasto. |
| Gasto | Costo de unidad o ubicacion con estado lineal y detalle. |
| Recuperacion de proveedor | Entrada real devuelta por un proveedor, separada del gasto bruto. El traslado al inquilino es un cargo. |
| Deposito | Fondo recibido y retenido como garantia; no constituye ingreso. |
| Incidencia | Problema o tarea operativa con responsables, evidencias, presupuestos y gastos. |
| Liquidacion | Estado de cuenta mensual de un propietario con revisiones y desembolsos. |
| ReportRun | Instantanea de un modo de calculo, datos y filtros compartida por pantalla y PDF. |
| Anticipo | Pago administrado reservado para una obligacion futura; no es ingreso, cobro aplicado ni liquidable antes de reconocer el cargo. |
| Correccion financiera | Revision o contramovimiento tipado que corrige un hecho sin ocultar su version original. |
| Criterio devengado | Considera cargos y gastos por su fecha economica aunque no se hayan cobrado o pagado. |
| Entrada de caja | Fondos administrados recibidos por `receivedOn`, o por `accountingOn` cuando se registran tarde. |
| Cobro aplicado | Importe asignado a un cargo por `appliedOn`. |
| Criterio de caja | Clasifica cada movimiento por su propia fecha efectiva civil. |

## 6. Modelo conceptual

```text
Organizacion
  |-- Miembros -- Usuario -- Roles -- Permisos
  |-- Partes -- Grants de representante -- Usuario
  |     |-- Distribuciones de titularidad -- Unidad
  |     |-- Participantes / Parte de facturacion -- Contrato
  |     `-- Huespedes / Responsables / Pagadores
  |-- Ubicaciones
  |     |-- Unidades -- Modalidades / Compatibilidad / Calendario
  |     |     |-- Contratos / Cuotas / Adendas
  |     |     |-- Reservas de alojamiento
  |     |     `-- Reservas de eventos
  |     `-- Tarifas / Cupos / Pases diarios
  |-- Cargos -- Aplicaciones / Reversiones -- Pagos
  |-- Gastos -- Detalles / Imputaciones / Aprobaciones / Recuperaciones
  |-- Depositos de garantia
  |-- Incidencias / Liquidaciones / Documentos
  `-- Auditoria / ReportRun / Trabajos / Notificaciones
```

### 6.1 Entidades principales

| Entidad | Responsabilidad y relaciones clave |
| --- | --- |
| `Organization` | Configuracion, branding, secuencias, catalogos, feriados, horarios y limite de aislamiento. |
| `User` | Identidad de acceso global por email. |
| `Membership` | Vincula usuario, organizacion, estado y roles. |
| `Role` / `Permission` | Autorizacion configurable por accion dentro de una organizacion. |
| `Party` | Persona fisica o juridica perteneciente a una sola organizacion. |
| `PartyContactVersion` | Historial de email, telefono y consentimiento por canal. |
| `OwnerRepresentativeGrant` | Relacion entre usuario y parte propietaria, con capacidades y estado. |
| `Location` | Agrupa unidades, recibe gastos y define tarifas y cupos de pases. |
| `Unit` | Bien operable, codigo, nombre, tipo fisico y estado administrativo. |
| `UnitModalityPeriod` | Vigencia semiabierta de una modalidad; otras modalidades pueden coexistir. |
| `UnitModalityCompatibilityRevision` | Version y vigencia de pares simetricos autorizados para una unidad. |
| `OwnershipDistribution` / `Line` | Distribucion atomica de propietarios, porcentajes y vigencia. |
| `LeaseContract` | Contrato finito con firma, vigencia, ciclo y parte de facturacion. |
| `ContractOccurrence` | Cuota futura con ciclo `SCHEDULED`, `ISSUED`, `CANCELLED` o `REPLACED` y cierre administrativo `OPEN`/`CLOSED`. |
| `ContractAmendment` / `RentScheduleVersion` | Adenda y cronograma pactado versionados. |
| `AccommodationBooking` / `NightRateLine` | Alojamiento por noches y desglose tarifario congelado. |
| `EventBooking` / `EventPackageSnapshot` | Evento por fecha-hora, paquete, aforo y buffers. |
| `AvailabilityBlock` | Bloqueo finito activo o cancelado. |
| `DayPass` / `DayPassLine` | Pase de ubicacion y cantidades por categoria. |
| `Charge` | Obligacion monetaria emitida con fecha de reconocimiento y periodo de servicio opcional. |
| `Payment` / `PaymentAllocation` | Cobro administrado y distribucion fechada contra cargos. |
| `AdvanceDesignation` | Reserva no patrimonial de un pago para contrato, alojamiento, evento o pase antes de `recognitionOn`. |
| `PaymentAllocationReversal` | Reversion parcial o total de una aplicacion. |
| `PaymentRefund` | Devolucion fechada de fondos externos disponibles desde un pago o credito de apertura. |
| `FinancialCorrection` | Contramovimiento tipado con signo derivado de su tipo, `accountingOn` y origen. |
| `LateRecordedMovement` | Metadata de un movimiento real omitido, con fecha economica original y periodo contable abierto de registro. |
| `Expense` / `ExpenseLine` | Gasto y detalle de conceptos cuyo total debe cuadrar. |
| `ExpenseAllocation` / `ExpenseRecovery` | Imputacion y recuperacion de un gasto sin alterar el bruto. |
| `SecurityDeposit` / `DepositMovement` | Cuenta de garantia y movimientos de recepcion, aplicacion, devolucion o correccion. |
| `MaintenanceIssue` | Flujo de incidencia, aprobaciones y costos relacionados. |
| `OwnerStatement` / `Revision` | Liquidacion por propietario y periodo con historial de revisiones. |
| `OwnerDisbursement` | Salida de caja registrada al pagar una liquidacion confirmada. |
| `OwnerFundReturn` | Entrada administrada por retorno real de un desembolso previo; no es ingreso. |
| `FinancialPeriod` | Mes financiero abierto o cerrado que controla movimientos retroactivos y liquidaciones. |
| `OpeningBatch` / `OpeningMovement` | Lote atomico; deuda actua como obligacion aplicable y credito como fuente aplicable/reembolsable, sin caja ni devengado del periodo actual. |
| `ReportRun` | Resultado canonico con creador, `accessMode`, parte representada, audiencia y `calculationMode`. |
| `Document` | Metadatos, audiencia congelada, version, politica y clave privada. |
| `Notification` | Canal, destinatario, plantilla, estado e intentos de entrega. |
| `AuditEvent` | Actor, accion, entidad, cambios relevantes y correlacion. |

## 7. Reglas e invariantes

### 7.1 Aislamiento multiempresa

- Toda entidad de negocio debe incluir `organizationId` directo o una relacion que lo haga verificable.
- La organizacion y el modo se obtienen de la ruta y se revalidan en cada solicitud; nunca se confia en el formulario o una seleccion global de sesion.
- Toda consulta y mutacion debe aplicar el alcance de organizacion antes de evaluar permisos funcionales.
- Un formulario conserva un sello de contexto; si otra pestana cambia organizacion o modo, la mutacion obsoleta se rechaza.
- Cada sesion de navegador mantiene una `contextGeneration`; el comando de cambiar organizacion, modo o parte representada la incrementa y toda mutacion exige la generacion vigente.
- Los modos `TEAM` y `PORTAL` son excluyentes y sus permisos no se unen.
- Las relaciones criticas deben usar restricciones compuestas que impidan referencias entre organizaciones.
- Las pruebas automatizadas deben intentar accesos cruzados con identificadores validos de otra organizacion.

### 7.2 Dinero, fechas e intervalos

- Todos los importes se guardan como enteros PYG y los porcentajes con cuatro decimales exactos; no se usa punto flotante.
- V1 no acepta otra moneda ni otra zona horaria que `America/Asuncion`.
- Toda fecha economica es una fecha civil con sufijo `On`, por ejemplo `recognitionOn`, `receivedOn`, `appliedOn`, `reversedOn`, `refundedOn`, `incurredOn`, `paidOn` y `disbursedOn`.
- `createdAt`, `confirmedAt`, `recordedAt` y auditoria son instantes UTC separados de las fechas economicas.
- Los intervalos canonicos usan `[fromOn, untilOn)`. Una fecha final contractual inclusiva se normaliza al dia siguiente como extremo `untilOn` exclusivo.
- El contrato conserva `agreedEndsOn` y `terminatedOn` como fechas inclusivas; `effectiveUntilOn` es el dia posterior a `terminatedOn` cuando existe y, en otro caso, a `agreedEndsOn`.
- Un evento guarda fecha-hora local completa, `America/Asuncion`, offset resuelto e instantes UTC; cambios posteriores de tzdata no reinterpretan una confirmacion.
- El redondeo se materializa una vez en lineas de la fuente mediante orden determinista; aplicaciones y liquidaciones no lo recalculan.
- Todo cargo tiene `recognitionOn`. Alquiler mensual usa el inicio del servicio, alojamiento usa check-in y evento usa la fecha local de inicio.
- V1 reconoce el cargo completo en `recognitionOn`; no prorratea automaticamente intervalos que cruzan meses.
- Los importes de movimientos fuente son enteros positivos; el tipo determina su signo contable. Solo resultados calculados, como el neto de liquidacion, pueden ser negativos.
- `reversedOn >= appliedOn`; `PaymentRefund.refundedOn` no antecede `Payment.receivedOn` u `OpeningMovement.openingOn`; `recoveredOn >= paidOn`; `DepositMovement.returnedOn` no antecede su recepcion u `openingOn`; y `OwnerFundReturn.returnedOn >= OwnerDisbursement.disbursedOn`.
- `accountingOn` debe pertenecer al periodo abierto elegido. Recepciones, devoluciones de proveedor, pagos de gastos, reembolsos, devoluciones de garantia y desembolsos confirmados no admiten fecha futura.
- Salvo el alta tardia definida en 7.3, el identificador de `FinancialPeriod` siempre se deriva de la fecha economica primaria `On`; el cliente no puede seleccionar un mes que no contenga esa fecha.

### 7.3 Historia, revisiones y correcciones

- Los borradores pueden editarse antes de emitir o confirmar.
- Un hecho confirmado conserva identidad estable e historial de revisiones.
- Si su periodo esta abierto y no tiene aplicaciones, reembolsos, documentos financieros, liquidaciones ni otras dependencias confirmadas, una correccion crea una nueva revision de la misma identidad.
- Si existe una dependencia o el periodo esta cerrado, la correccion crea un contramovimiento tipado, fechado y enlazado; no modifica el original.
- Todo ajuste guarda `accountingOn`, `recordedAt`, actor, motivo, correlacion y origen. El usuario puede elegir cualquier periodo abierto no anterior al origen o reabrir el original cuando sea legal.
- `recordedAt` puede ser posterior a `accountingOn`; preserva cuando se descubrio/registro la correccion y nunca se retrofecha.
- Un movimiento real omitido no es una correccion porque carece de origen. Si su periodo original sigue abierto o puede reabrirse, se registra normalmente con su fecha economica real.
- Si el periodo original no puede reabrirse, el comando crea un solo hecho financiero ordinario confirmado del tipo real correspondiente y un `LateRecordedMovement` asociado con fecha economica real, `recordedAt` actual, motivo, evidencia y `accountingOn` dentro de un periodo abierto no anterior al hecho.
- `LateRecordedMovement` es metadata uno-a-uno y no contabiliza importes propios. Los deltas del hecho enlazado pertenecen solo a `accountingOn`; `CURRENT_RESTATED` puede explicar la fecha economica original sin mover el periodo oficial, duplicar caja ni inventar un contramovimiento.
- Una aplicacion admite reversiones parciales inmutables; su estado total, parcial o revertido es derivado.
- `FinancialCorrection` cubre cargos, pagos, aplicaciones, reembolsos, garantias, gastos, devoluciones de proveedor, desembolsos, retornos y movimientos de apertura. Cada tipo define efecto sobre deuda, caja, fondos retenidos y propietario.
- Cada correccion materializa deltas separados de devengado, deuda, caja, fondos retenidos y saldo de propietario. La combinacion permitida depende del tipo y debe cuadrar a cero con su origen cuando sea una reversion total.
- Los tipos minimos son los enumerados en la matriz siguiente; un tipo no puede emitir deltas fuera de su fila.
- Contratos, adendas, cronogramas, titularidades, modalidades, tarifas y documentos conservan las versiones exigidas por su politica.
- Un cambio posterior no recalcula instantaneas o liquidaciones ya confirmadas fuera de las reglas expresas de reapertura.

La matriz minima de efectos correctivos es:

| Tipo | Devengado / gasto | Deuda o fuente | Caja administrada | Fondos retenidos | Saldo liquidable de propietario |
| --- | --- | --- | --- | --- | --- |
| Ajuste de cargo | Ajusta ingreso | Ajusta deuda | Sin efecto | Sin efecto | Sin efecto directo hasta corregir o crear aplicacion |
| Correccion de pago sin movimiento real | Sin efecto | Ajusta fuente disponible | Ajusta caja registrada en igual sentido | Sin efecto | Sin efecto hasta corregir aplicaciones |
| Reversion de aplicacion | Sin efecto | Restaura deuda y fuente | Sin efecto | Sin efecto | Revierte Cobro aplicado original |
| Correccion de reembolso | Sin efecto | Restaura o reduce fuente | Revierte el efecto de caja del reembolso | Sin efecto | Sin efecto |
| Correccion de recepcion de garantia | Sin efecto | Sin efecto | Ajusta caja solo si no hubo movimiento real | Ajusta retenido en igual sentido | Sin efecto |
| Reversion de aplicacion de garantia | Sin efecto | Restaura deuda y neutraliza fuente interna | Sin efecto | Restaura retenido | Revierte Cobro aplicado original |
| Ajuste de gasto incurrido | Ajusta gasto | Sin efecto | Sin efecto | Sin efecto | Sin efecto directo hasta pago o recuperacion real |
| Correccion de pago de gasto | Sin efecto | Sin efecto | Revierte salida registrada si no fue real | Sin efecto | Revierte gasto pagado atribuible |
| Correccion de devolucion de proveedor | Sin efecto | Sin efecto | Revierte entrada registrada si no fue real | Sin efecto | Revierte devolucion atribuible |
| Correccion de desembolso | Sin efecto | Sin efecto | Revierte salida registrada si no fue real | Sin efecto | Restaura saldo por desembolsar |
| Correccion de retorno de desembolso | Sin efecto | Sin efecto | Revierte entrada registrada si no fue real | Sin efecto | Reduce saldo por desembolsar restaurado |
| Ajuste de deuda de apertura | Sin devengado | Ajusta deuda inicial | Sin efecto | Sin efecto | Sin efecto directo hasta su aplicacion |
| Ajuste de credito de apertura | Sin efecto | Ajusta fuente inicial | Sin efecto | Sin efecto | Sin efecto hasta su aplicacion |
| Ajuste de garantia de apertura | Sin efecto | Sin efecto | Sin efecto | Ajusta retenido inicial | Sin efecto |
| Ajuste de liquidacion de apertura | Sin efecto | Sin efecto | Sin efecto | Sin efecto | Ajusta saldo inicial pagable |

- Una correccion compuesta crea atomicamente todas las filas requeridas por la matriz y bloquea fuentes/destinos en orden determinista.
- Si hubo movimiento real posterior, se usa el hecho real correspondiente, como reembolso, devolucion de proveedor o `OwnerFundReturn`, y no una correccion ficticia de caja.

Los ciclos financieros obligatorios son:

- Un cargo borrador puede descartarse; un cargo emitido permanece. Antes de `recognitionOn`, una conciliacion de cancelacion puede marcarlo `CANCELLED` o `REPLACED` sin borrarlo; desde `recognitionOn` se corrige por revision o contramovimiento. Abierto, parcialmente pagado, pagado y vencido son derivados.
- Un pago externo pasa de borrador a confirmado. Un borrador puede descartarse; un confirmado se corrige segun el movimiento real y el modelo hibrido.
- Una fuente interna por deposito se crea confirmada, sin entrada de caja, con fecha efectiva igual a su aplicacion.
- Una aplicacion permanece confirmada y puede recibir reversiones parciales o totales con `reversedOn`; nunca se edita en sitio.
- Un reembolso permanece en borrador hasta la salida real; al confirmar fija importe y `refundedOn`.
- Un movimiento de deposito borrador puede descartarse; al confirmar permanece y su tipo determina si aumenta o reduce el saldo retenido.
- Un gasto conserva `incurredOn` al pasar a incurrido y `paidOn` al pasar a pagado. Pagarlo no elimina el devengado.
- Revisiones vigentes, hechos emitidos/confirmados y contramovimientos confirmados participan en reportes; los derivados no sustituyen el historial.

### 7.4 Titularidad y atribucion

- La titularidad se confirma como una distribucion completa y atomica, nunca linea por linea.
- Cada distribucion usa `[startsOn, untilOn)`, donde `untilOn` nulo representa vigencia abierta, porcentajes de cuatro decimales y suma exactamente `100.0000 %`.
- Dos distribuciones no se superponen y pueden ser contiguas.
- Cargos guardan el snapshot aplicable en `recognitionOn`; cobros y reversiones posteriores conservan propietario y porcentaje de ese snapshot.
- Gastos se atribuyen segun la titularidad en `incurredOn`, aunque la imputacion se confirme despues.
- `allocatedOn` selecciona las unidades objetivo y por defecto coincide con `incurredOn`; altas y bajas posteriores no recalculan lineas.
- Cambios retroactivos que intersectan dependencias confirmadas se bloquean y se resuelven mediante ajustes, no reescribiendo snapshots.
- Todo reparto materializa porcentajes, importes enteros y residuo determinista en la fuente.
- Todo cargo o gasto atribuible exige exactamente una distribucion aplicable en su fecha economica. Confirmar una operacion y cambiar la distribucion se serializan por unidad.

### 7.5 Modalidades, calendario y disponibilidad

- Tradicional, comercial, alojamiento temporario y eventos tienen vigencias independientes; modalidades distintas pueden estar activas simultaneamente.
- Una operacion debe quedar contenida en una vigencia de su modalidad.
- La matriz por unidad es simetrica y deniega por defecto coincidencias entre modalidades distintas.
- Compromisos de la misma modalidad nunca se superponen. Compromisos de modalidades distintas solo coinciden cuando la matriz lo autoriza y no existe bloqueo.
- Cada revision de matriz guarda pares canonicos, vigencia y version; la operacion confirmada conserva la revision utilizada. V1 no modela recursos internos ni suma capacidades entre modalidades.
- Reservas confirmadas, check-in y check-out conservan su intervalo historico. Borradores, canceladas y no presentadas no bloquean despues de su transicion.
- Bloqueos son intervalos finitos activos o cancelados y son incompatibles con todo compromiso.
- Alojamiento incluye buffers y horarios programados; eventos incluyen buffer previo y posterior.
- Todo compromiso materializa `[calendarStartsAt, calendarEndsAt)` en UTC: contratos desde el inicio local de `startsOn` hasta el inicio local de `effectiveUntilOn`; alojamiento y eventos desde sus horarios locales expandidos por buffers; bloqueos desde limites locales explicitos.
- Vigencia de modalidad y compatibilidad deben cubrir todo el intervalo de calendario expandido, incluidos buffers.
- Todo cambio de contrato, reserva, bloqueo, modalidad, compatibilidad o archivo toma el mismo bloqueo transaccional por unidad y revalida el calendario.
- El estado administrativo se muestra separado del operativo; ante conflicto, el calendario prevalece y nunca permite sobreocupacion.
- Pases diarios no ocupan unidades: consumen un cupo transaccional de ubicacion y franja.

### 7.6 Idempotencia

- Cada comando sensible usa `Idempotency-Key` por principal, organizacion o scope, `accessMode`, parte representada, target y comando, con hash del payload.
- Misma clave y payload reproduce el resultado; la misma clave con otro payload devuelve conflicto.
- Workers derivan una clave determinista de origen, revision y efecto y la reutilizan en todos los reintentos.
- Una ocurrencia contractual se identifica por contrato, intervalo de servicio, concepto e identidad de ocurrencia.
- Una notificacion automatica se identifica por evento, destinatario, canal y plantilla.
- Reintentar no puede duplicar cuotas, cargos, pagos, pases, liquidaciones, PDF ni mensajes.
- Idempotencia no reemplaza transacciones, bloqueos o restricciones unicas.

### 7.7 Periodos financieros y cuotas

- Existe un periodo por mes calendario, pero sus estados son independientes: no se exige cerrar meses en orden.
- El primer hecho con fecha economica dentro de un mes crea atomicamente su periodo abierto si no existe.
- Un mes solo puede cerrarse despues de terminar en `America/Asuncion`.
- Cada cuota contractual tiene cierre administrativo independiente. Congela importe y detalle, pero no paga, condona ni detiene deuda o mora.
- Todas las cuotas con `recognitionOn` en el mes deben estar cerradas antes del cierre financiero; no existe excepcion de cuota abierta justificada.
- El cierre bloquea cargos automaticos faltantes y mutaciones en curso; cobros sin aplicar y gastos declarados sin atribuir generan advertencia y motivo obligatorio.
- Todo movimiento y el cierre bloquean la misma fila de periodo; quien confirma primero determina el resultado.
- Cargos usan `recognitionOn`, pagos `receivedOn`, aplicaciones `appliedOn`, reversiones `reversedOn`, reembolsos `refundedOn`, gastos `incurredOn`/`paidOn` y desembolsos `disbursedOn`.
- Para un hecho ordinario marcado por `LateRecordedMovement`, la pertenencia oficial al periodo se deriva exclusivamente de `accountingOn`; su fecha economica original permanece para cronologia, controles y explicacion reformulada.
- Una liquidacion solo se confirma sobre un periodo cerrado.
- Un periodo puede reabrirse con liquidaciones parcialmente desembolsadas si ninguna revision queda por debajo de lo ya desembolsado.
- Si existe una liquidacion totalmente desembolsada, el periodo no se reabre. La correccion se publica en un periodo abierto elegido no anterior al origen.
- Una fuente atribuible aparece una sola vez en la revision vigente de una liquidacion.

### 7.8 Visibilidad historica y documentos

- La visibilidad pertenece a la parte propietaria y se ejerce mediante un grant de representante activo.
- Un grant nuevo habilita todo el historial elegible; una titularidad finalizada no habilita operacion posterior.
- La vista financiera usa snapshots y lineas atribuidas. Cobros sin aplicar solo aparecen en la bandeja organizacional.
- Fuentes compartidas no se exponen al propietario: la liquidacion muestra importes agregados autorizados, no el pago ni comprobante padre.
- Cada version documental materializa audiencia y periodo efectivo de fuente; cambios posteriores no recalculan destinatarios.
- Solo usuarios autenticados descargan documentos. Las partes sin cuenta no reciben adjuntos, URL ni tokens de capacidad.
- La politica de versiones es configurable por tipo, conserva por defecto y solo afecta versiones futuras. Si ordena eliminar contenido reemplazado, conserva evento, autor, fecha y checksum.

## 8. Requisitos funcionales

### 8.1 Organizaciones y onboarding

- `ORG-01`: el superadministrador debe poder crear una organizacion y enviar invitacion a su primer administrador.
- `ORG-02`: una persona debe poder autorregistrarse, verificar su email y crear una organizacion activa.
- `ORG-03`: suspender debe bloquear equipo, portal, invitaciones, descargas, exportaciones, jobs y mensajes de negocio; callbacks, scanner, limpieza y backups tecnicos pueden continuar.
- `ORG-04`: cada organizacion configura nombre legal y comercial, RUC opcional, direccion, contactos, logo y prefijo de recibos.
- `ORG-05`: PYG y `America/Asuncion` son fijos y no editables en V1.
- `ORG-06`: la organizacion configura avisos, mora, categorias, tipos de unidad, medios de pago, feriados, horarios, buffers y politicas de aprobacion.
- `ORG-06A`: la finalizacion natural de contratos se configura como automatica o manual; el valor inicial es automatico.
- `ORG-07`: reactivar crea una vista previa de cargos, mora y trabajos omitidos; la ejecucion posterior es autorizada e idempotente.
- `ORG-08`: el catch-up reabre un periodo cuando sea legal o publica un ajuste enlazado en un periodo abierto elegido.
- `ORG-09`: avisos historicos obsoletos no se envian al reactivar.
- `ORG-10`: el sistema incluye valores iniciales editables, excepto moneda y zona.
- `ORG-11`: la facturacion de la suscripcion SaaS permanece fuera de V1.

### 8.2 Identidad, roles y permisos

- `IAM-01`: el acceso debe usar email verificado y contrasena.
- `IAM-02`: deben existir invitacion, aceptacion, recuperacion de contrasena y cierre de sesiones activas.
- `IAM-03`: un usuario puede pertenecer a varias organizaciones; organizacion y modo se eligen en la ruta y se revalidan por solicitud.
- `IAM-04`: un formulario con contexto obsoleto debe fallar y nunca ejecutarse en otra organizacion.
- `IAM-05`: el modo `TEAM` usa roles y el modo `PORTAL` usa grants patrimoniales; sus permisos no se unen.
- `IAM-06`: los roles internos son aditivos y habilitan acciones sobre toda la organizacion en V1.
- `IAM-07`: un gestor no puede conceder un permiso que no posee ni dejar cero administradores efectivos.
- `IAM-08`: el sistema ofrece plantillas editables de administrador, operador, cobranzas y mantenimiento.
- `IAM-09`: `OwnerRepresentativeGrant` vincula muchos usuarios con muchas partes propietarias y define ver, descargar y aprobar.
- `IAM-09A`: una solicitud `PORTAL` incluye `representedOwnerPartyId`; tener otros grants no amplia ese alcance.
- `IAM-10`: un grant activo habilita todo el historial elegible de la parte, no solo el posterior a su alta.
- `IAM-11`: revocar membresia, rol o grant surte efecto en la siguiente solicitud, job y descarga.
- `IAM-12`: una invitacion solo puede aceptarla el usuario cuyo email verificado coincide con el destinatario.
- `IAM-13`: plataforma puede enviar una invitacion fija de recuperacion, pero no aceptar ni suplantar al destinatario.
- `IAM-14`: ver y exportar son permisos distintos.
- `IAM-15`: cambios de acceso, modo, roles, grants y recuperacion quedan auditados.

### 8.3 Partes

- `PTY-01`: una parte puede ser persona fisica o juridica.
- `PTY-02`: debe admitir nombre, documento o RUC, contactos, direccion, observaciones y archivos.
- `PTY-03`: cada `Party` pertenece a una organizacion; el `User` global no fusiona partes de organizaciones distintas.
- `PTY-04`: una misma parte puede actuar en varios roles sin duplicar su identidad local.
- `PTY-05`: coincidencias por documento, RUC, email o telefono son advertencias, nunca bloqueos automaticos.
- `PTY-06`: email y telefono actuales son campos directos, pero cada valor y consentimiento conserva historial versionado.
- `PTY-07`: cambiar un contacto reinicia su consentimiento y no redirige mensajes pendientes.
- `PTY-08`: cada contrato o reserva identificada tiene una sola parte de facturacion; el pagador real se registra aparte.
- `PTY-09`: archivar se rechaza mientras existan titularidades, contratos, reservas o aprobaciones activas.
- `PTY-10`: una parte archivada no entra en relaciones nuevas, pero puede saldar y consultar su historia.
- `PTY-11`: una venta anonima de pase puede omitir parte y responsable.

### 8.4 Ubicaciones y unidades

- `PRT-01`: una organizacion puede crear cualquier cantidad de ubicaciones dentro del limite operativo contratado externamente.
- `PRT-02`: una ubicacion admite nombre, codigo normalizado unico por organizacion, direccion, descripcion, contactos, archivos y estado.
- `PRT-03`: una ubicacion puede contener una o muchas unidades.
- `PRT-04`: la unidad debe admitir codigo unico dentro de la ubicacion, nombre visible editable, tipo fisico, descripcion y archivos.
- `PRT-05`: si el usuario no asigna un nombre, el sistema debe sugerir `<prefijo-ubicacion>-<secuencia>`; si no existe prefijo, `Unidad <secuencia>`.
- `PRT-06`: el usuario puede editar el nombre sugerido sin alterar identificadores internos ni historia.
- `PRT-07`: los tipos fisicos deben ser catalogos configurables, por ejemplo casa, duplex, departamento, cabana y salon comercial.
- `PRT-08`: una unidad admite vigencias independientes y simultaneas de tradicional, comercial, alojamiento temporario y eventos.
- `PRT-09`: vigencias de la misma modalidad no se superponen; las de modalidades distintas pueden hacerlo.
- `PRT-10`: cada unidad configura una matriz simetrica de compatibilidad; una pareja no declarada se deniega.
- `PRT-11`: cambiar vigencia o compatibilidad se rechaza si vuelve incompatible un compromiso confirmado.
- `PRT-12`: la unidad puede marcarse en venta sin bloquear contratos o reservas.
- `PRT-13`: estado administrativo manual y estado operativo derivado se muestran como dimensiones distintas.
- `PRT-14`: estados administrativos son borrador, activo, inactivo y archivado; no reservan ni liberan calendario por si solos.
- `PRT-14A`: el operativo se deriva por modalidad y muestra compromisos y bloqueos activos, no una etiqueta unica que oculte coincidencias compatibles.
- `PRT-14B`: el calendario prevalece ante contradicciones y nunca permite una superposicion por un estado manual; mantenimiento requiere un bloqueo.
- `PRT-15`: horarios y buffers de organizacion pueden reemplazarse por unidad.
- `PRT-16`: archivar una unidad se rechaza con ocupaciones futuras; despues permite pagos, ajustes, devoluciones y reportes historicos.
- `PRT-17`: inactivar una ubicacion se rechaza mientras tenga unidades operativas o pases futuros y no produce cascada.
- `PRT-18`: las tarifas y cupos de pases diarios se configuran exclusivamente por ubicacion.

### 8.5 Titularidad y copropiedad

- `OWN-01`: una unidad admite una o varias partes dentro de una distribucion completa.
- `OWN-02`: la distribucion usa `[startsOn, untilOn)`, admite `untilOn` nulo, usa cuatro decimales y suma `100.0000 %`.
- `OWN-03`: el cambio se edita como borrador y se confirma atomicamente, sin estados intermedios de 0 % o 200 %.
- `OWN-04`: distribuciones de una unidad no se superponen y pueden ser contiguas.
- `OWN-05`: un cambio conserva la distribucion historica y no recalcula snapshots confirmados.
- `OWN-06`: una correccion retroactiva con dependencias se bloquea y se resuelve mediante ajustes auditados.
- `OWN-07`: el administrador crea grants de representantes vinculados a cada parte propietaria.
- `OWN-08`: terminar la titularidad conserva acceso historico elegible hasta revocar el grant.
- `OWN-09`: reportes y liquidaciones respetan porcentaje e importe materializados por fecha economica.

### 8.6 Contratos tradicionales y comerciales

- `CTR-01`: cada contrato refiere una unidad; contratos de la misma modalidad no se superponen y modalidades contractuales distintas solo coinciden si la matriz lo autoriza.
- `CTR-02`: una parte puede mantener contratos separados sobre varias unidades.
- `CTR-03`: admite varios participantes y garantes, pero exactamente una parte de facturacion.
- `CTR-04`: cambiar la parte de facturacion exige terminar y crear un contrato nuevo enlazado.
- `CTR-05`: guarda `signedOn` opcional y `startsOn`/`agreedEndsOn` obligatorios; firma y vigencia son independientes.
- `CTR-06`: `agreedEndsOn` conserva el ultimo dia pactado inclusivo y `terminatedOn` el ultimo dia efectivo inclusivo; el calendario usa `effectiveUntilOn` exclusivo.
- `CTR-07`: contiene modalidad, ciclo, regla de vencimiento explicita, cronograma, mora, senia tipada y documentos opcionales.
- `CTR-08`: los estados son borrador, activo, finalizado y rescindido; futuro, vigente, vencido y proximo a vencer son fases derivadas.
- `CTR-09`: activar valida unidad, titularidad, modalidad, compatibilidad, calendario, partes y cronograma.
- `CTR-10`: cada contrato elige ciclo por mes calendario o ancla aniversario; meses cortos usan el ultimo dia sin perder el ancla original.
- `CTR-10A`: calendario genera primer tramo desde `startsOn` hasta el primer dia del mes siguiente y luego meses civiles; aniversario genera limites desde el dia original. El ultimo tramo se recorta en `effectiveUntilOn`.
- `CTR-10B`: la regla de vencimiento declara explicitamente si vence antes, al inicio o despues del servicio y materializa `dueOn` en cada ocurrencia.
- `CTR-11`: periodos iniciales o finales parciales tienen importe explicito y no se prorratean automaticamente.
- `CTR-12`: activar materializa todas las ocurrencias futuras hasta `effectiveUntilOn`, con servicio, fecha de cargo, vencimiento, importe y version.
- `CTR-13`: el ciclo de ocurrencia es `SCHEDULED -> ISSUED`; una adenda puede marcar una futura `REPLACED` y una terminacion `CANCELLED`, sin borrar filas.
- `CTR-14`: la ocurrencia se vuelve cargo emitido al inicio del servicio, una sola vez.
- `CTR-15`: el cierre administrativo `OPEN/CLOSED` es independiente del ciclo; cerrar congela detalle, no deuda ni mora.
- `CTR-16`: las ocurrencias con `recognitionOn` del mes deben cerrarse antes del periodo; reabrir una exige que el periodo este abierto, permiso y motivo.
- `CTR-17`: una adenda versiona fecha efectiva, motivo, documento opcional y cronograma; marca reemplazadas solo ocurrencias futuras no emitidas.
- `CTR-17A`: si la adenda cae dentro de una ocurrencia futura, el operador debe dividirla en lineas o cargos explicitos; no existe prorrateo automatico.
- `CTR-18`: cargos emitidos se corrigen mediante revision permitida o ajuste, nunca sobrescribiendo historia.
- `CTR-19`: la finalizacion natural es automatica por defecto y puede configurarse manual por organizacion.
- `CTR-20`: en modo manual, al vencer queda activo con fase derivada vencido, pero disponibilidad se libera en `effectiveUntilOn`.
- `CTR-21`: la terminacion anticipada marca futuras como canceladas y concilia la ocurrencia intersectada sin prorrateo automatico.
- `CTR-22`: finalizar o rescindir conserva deuda, pagos, cuotas, adendas, documentos y garantia.
- `CTR-23`: una renovacion crea contrato enlazado y puede recibir transferencia interna de garantia si conserva parte de facturacion.
- `CTR-24`: contratos finalizados y rescindidos conservan historia; una alta retroactiva aplica las mismas reglas de modalidad y matriz.
- `CTR-25`: los conflictos se resuelven por calendario y matriz; la marca en venta no participa.
- `CTR-26`: el sistema avisa vencimientos, cuotas y contratos por finalizar segun configuracion.

### 8.7 Mora

- `MOR-01`: la organizacion define una regla por defecto y cada contrato puede reemplazarla.
- `MOR-02`: el modo manual debe calcular dias de atraso y permitir agregar un cargo de mora con detalle.
- `MOR-03`: el modo automatico debe admitir dias de gracia y un recargo unico fijo o porcentual sobre saldo vencido.
- `MOR-04`: cada cargo congela la version de regla vigente al emitirse.
- `MOR-05`: un worker tardio reconstruye el saldo al fin de la gracia, no el saldo del dia de ejecucion.
- `MOR-06`: cada cargo guarda `graceUntilOn` exclusivo; un cobro suficiente con `receivedOn < graceUntilOn` suspende mora y genera alerta.
- `MOR-07`: un mismo cobro no aplicado no protege varias deudas; se reserva virtualmente por `dueOn`, `recognitionOn` e ID de cargo, sin crear aplicaciones.
- `MOR-08`: el recargo debe ser idempotente por cargo y regla congelada.
- `MOR-09`: un recargo emitido se corrige con el modelo hibrido de `FIN-04`; un borrador puede anularse con motivo.

### 8.8 Calendario, alojamiento, eventos y pases

#### 8.8.1 Calendario comun

- `CAL-01`: contratos, alojamientos, eventos, buffers y bloqueos deben mostrarse en el mismo calendario por unidad.
- `CAL-02`: confirmar, reprogramar, terminar, cancelar o bloquear toma el mismo control transaccional por unidad.
- `CAL-03`: un bloqueo se crea activo con intervalo finito, no tiene borrador y se cancela sin borrar historia.
- `CAL-04`: estados confirmada, check-in y check-out conservan el intervalo; borrador, cancelada y no presentada no bloquean.
- `CAL-05`: la compatibilidad entre modalidades se valida de nuevo despues de adquirir el bloqueo.
- `CAL-06`: el perdedor de una carrera recibe `409` sin cargos, documentos ni compromisos huerfanos.

#### 8.8.2 Alojamiento temporario

- `RSV-A01`: `AccommodationBooking` contiene unidad, parte de facturacion, huespedes, `checkInOn`, `checkOutOn`, horarios, buffers, notas y origen manual.
- `RSV-A02`: materializa una linea tarifaria por noche segun tarifa, fin de semana o feriado configurable.
- `RSV-A02A`: cada noche se clasifica por su fecha local de inicio; precedencia: tarifa explicita de fecha, feriado, fin de semana y tarifa base.
- `RSV-A03`: cada linea y la version tarifaria quedan congeladas al confirmar.
- `RSV-A04`: un precio acordado distinto conserva el calculo y agrega descuento o recargo explicito con motivo.
- `RSV-A05`: horarios predeterminados se configuran por organizacion, pueden reemplazarse por unidad y se congelan en la reserva.
- `RSV-A06`: los estados siguen `borrador -> confirmada -> check-in -> check-out`; desde confirmada tambien cancelada o no presentada. Los terminales no se reactivan.
- `RSV-A06A`: check-in y check-out guardan `checkedInAt` y `actualCheckOutAt` UTC, separados de fechas y horarios programados.
- `RSV-A07`: reprogramar crea revision, revalida calendario y cotiza con tarifas actuales por defecto; conservar la version original para las noches nuevas exige motivo y la diferencia corrige el cargo segun `FIN-04`.
- `RSV-A08`: autorizar late check-out crea una revision con `authorizedLateCheckOutAt`, recalcula `calendarEndsAt` bajo bloqueo y se limita al siguiente compromiso incompatible menos limpieza; sin compromiso posterior usa `latestLateCheckOutTime` de unidad.
- `RSV-A08B`: `actualCheckOutAt` registra la salida real y permanece separado del horario autorizado.
- `RSV-A08C`: el cargo de late check-out usa `recognitionOn` de la fecha local de la salida real.
- `RSV-A08A`: una salida real posterior al maximo autorizado crea incidencia y cargo adicional, pero no desplaza ni cancela automaticamente el siguiente compromiso.
- `RSV-A09`: salida anticipada usa conciliacion manual; no reduce precio ni libera noches silenciosamente.
- `RSV-A10`: consumos, danos y extras posteriores crean cargos enlazados, no editan el precio confirmado.
- `RSV-A11`: cancelacion y no-show manual usan conciliacion guiada de cargos, aplicaciones, anticipo, garantia, penalidad y reembolso.
- `RSV-A12`: el cargo base se emite al confirmar, pero se reconoce completo en `checkInOn` aunque la estadia cruce mes.

#### 8.8.3 Eventos

- `RSV-E01`: `EventBooking` es una entidad separada con unidad, parte de facturacion, responsable, inicio y fin local completos, UTC resuelto, asistentes y notas.
- `RSV-E02`: el intervalo puede cruzar medianoche y debe tener fin posterior al inicio.
- `RSV-E03`: la unidad define aforo; confirmar o aumentar asistentes nunca puede excederlo.
- `RSV-E04`: paquetes configurables por franja, tipo de dia y rango de asistentes fijan precio, inclusiones y buffers.
- `RSV-E05`: confirmar congela una revision de paquete, asistentes, precio, ajustes, aforo y buffers.
- `RSV-E06`: todo cambio pre-check-in crea revision, toma bloqueo de unidad, revalida aforo/calendario y corrige el cargo segun `FIN-04`; despues, asistentes extra crean cargo enlazado.
- `RSV-E07`: un evento que excede su fin guarda `actualEndedAt`, crea incidencia y cargo, sin desplazar operaciones posteriores.
- `RSV-E07A`: el cargo por exceso usa `recognitionOn` de la fecha local del fin real.
- `RSV-E08`: estados son borrador, confirmada, check-in, check-out, cancelada y no presentada, con el mismo grafo estricto de alojamiento.
- `RSV-E08A`: inicio y fin reales guardan `checkedInAt` y `actualEndedAt` UTC, sin reescribir el intervalo confirmado.
- `RSV-E09`: el cargo base se emite al confirmar con `recognitionOn` en la fecha local de inicio; se reconoce al llegar esa fecha, no al confirmar.

#### 8.8.4 Pases diarios

- `PAS-01`: `DayPass` pertenece a una ubicacion, fecha, franja y lineas de cantidad por categoria.
- `PAS-02`: categorias, precios y cupos se configuran solo por ubicacion y se congelan al confirmar.
- `PAS-02A`: cada franja materializa hora local de inicio y fin como intervalo semiabierto no vacio; dos franjas vigentes de una ubicacion no pueden solaparse.
- `PAS-02B`: una franja con pases futuros activos no permite cambiar intervalo o cupo en sitio; el cambio crea una version futura que vuelve a validar la ausencia de solape.
- `PAS-03`: el cupo bloquea `(locationId, dateOn)`, revalida todas las franjas de esa fecha y suma cantidades activas de todas las categorias en la franja elegida; no suma huespedes ni eventos.
- `PAS-04`: confirmar crea atomicamente pase, cargo emitido, pago total y aplicacion o anticipo designado; no admite deuda ni pago parcial.
- `PAS-04A`: el cargo de servicio usa `recognitionOn` igual a la fecha del pase. Si el pago ocurre antes, queda designado como anticipo y se aplica al reconocer el cargo.
- `PAS-05`: `buyerPartyId` y responsable son opcionales y distintos del pagador. Es identificada si tiene comprador o responsable; la parte de facturacion es el comprador o, en su ausencia, el responsable. Solo es anonima si no tiene ninguno.
- `PAS-06`: estados son `DRAFT -> CONFIRMED -> USED`; `CANCELLED` solo procede desde borrador o confirmado y usado es terminal.
- `PAS-07`: cancelar libera cupo. Una venta identificada por comprador o responsable libera anticipo o, si ya fue reconocida, corrige cargo/aplicacion; el reembolso se confirma aparte al devolver dinero.
- `PAS-08`: una venta anonima, sin comprador ni responsable, confirmada es no reembolsable y debe advertirlo antes del pago.
- `PAS-08A`: antes de la fecha del pase, cancelar una venta anonima marca el cargo futuro `REPLACED`, lo enlaza y reemplaza atomicamente por una penalidad no reembolsable con `recognitionOn=cancelledOn`, y convierte el anticipo en aplicacion con `appliedOn=cancelledOn`. Despues de reconocer, revierte/corrige cargo y aplicacion antes de emitir y aplicar la penalidad con `recognitionOn=cancelledOn`. No crea reembolso ni fecha efectiva futura.
- `PAS-09`: el ingreso pertenece a la organizacion, conserva ubicacion como dimension y no entra en liquidaciones de propietarios.
- `PAS-10`: V1 no importa ni exporta disponibilidad a plataformas externas.

### 8.9 Cargos, pagos y recibos

- `FIN-01`: un cargo identifica parte de facturacion cuando exista, alcance, concepto, `recognitionOn`, servicio opcional, `issuedOn`, `dueOn`, importe y origen.
- `FIN-02`: alquiler, mora, servicio, alojamiento, evento, pase, gasto trasladado y otros conceptos configurables deben permanecer diferenciados.
- `FIN-03`: `DRAFT`, `ISSUED`, `CANCELLED` y `REPLACED` son estados persistidos del cargo; los dos ultimos solo proceden antes de `recognitionOn`, conservan el cargo y enlazan la conciliacion. Abierto, parcialmente pagado, pagado y vencido son derivados.
- `FIN-04`: una correccion sigue el modelo hibrido: revision en periodo abierto sin dependencias o contramovimiento tipado en los demas casos.
- `FIN-05`: V1 confirma un movimiento de caja solo cuando ocurre una entrada o salida real bajo administracion. Un pago directo al propietario nunca se registra ni cancela deuda salvo recepcion posterior efectiva por la organizacion.
- `FIN-05A`: `paidOn`, `recoveredOn`, `refundedOn`, `returnedOn` y `disbursedOn` solo se fijan al ocurrir la salida o entrada administrada correspondiente; una intencion previa permanece en borrador.
- `FIN-06`: un pago externo registra parte de facturacion, pagador real, `receivedOn`, medio, importe, referencia, observacion y comprobante opcional.
- `FIN-07`: una venta anonima de pase puede registrar un pago sin `Party`, ligado exclusivamente al pase.
- `FIN-08`: los medios iniciales son efectivo, transferencia y otro; la organizacion puede ampliarlos.
- `FIN-09`: un pago se aplica total o parcialmente a cargos o deuda de apertura de la misma organizacion y parte de facturacion.
- `FIN-10`: aplicaciones netas, reembolsos y designaciones activas no pueden superar la fuente, sea pago o credito de apertura; una aplicacion no supera el saldo de la obligacion.
- `FIN-11`: el remanente no aplicado ni designado permanece como cobro administrado disponible y solo se muestra en la bandeja organizacional.
- `FIN-12`: confirmar genera numero secuencial y recibo interno no fiscal con parte de facturacion y pagador real cuando existan.
- `FIN-13`: un pago confirmado que nunca represento movimiento real se corrige mediante revision o contramovimiento que neutraliza la caja registrada sin afirmar una nueva entrada o salida real; si el dinero se recibio y despues salio se usa reembolso.
- `FIN-14`: factura externa admite numero, timbrado, `issuedOn` y archivo sin emision ni validacion fiscal.
- `FIN-15`: `PaymentAllocation` guarda `appliedOn` y no puede anteceder la disponibilidad de su fuente.
- `FIN-15A`: `appliedOn` tampoco puede anteceder `recognitionOn` del cargo; antes de esa fecha se usa `AdvanceDesignation`.
- `FIN-16`: si se aplica al confirmar, `appliedOn` coincide con `receivedOn`; una aplicacion posterior pertenece a su propio mes.
- `FIN-17`: una aplicacion admite varias reversiones parciales inmutables con importe, `reversedOn`, motivo y enlace.
- `FIN-18`: la suma revertida no supera el importe original; saldo del cargo y fuente se recalculan bajo bloqueos deterministas.
- `FIN-19`: entrada de caja usa `receivedOn`, cobro aplicado `appliedOn` y reversion `reversedOn`; no se mezclan.
- `FIN-20`: la atribucion de toda aplicacion y reversion procede del snapshot del cargo en `recognitionOn`.
- `FIN-21`: un reembolso exige una fuente confirmada `Payment` u `OpeningMovement(CREDIT)`, saldo disponible bloqueado, beneficiario elegido sin valor predeterminado, importe, medio, referencia y motivo.
- `FIN-22`: el reembolso permanece en borrador hasta la salida real y entonces fija `refundedOn` y `confirmedAt`.
- `FIN-23`: antes de reembolsar se confirman las reversiones necesarias; el reembolso reduce caja, no ingreso ni gasto, y nunca crea una entrada para el credito de apertura.
- `FIN-24`: una cancelacion con retencion conserva o emite penalidad, aplica la fuente elegida y deja el reembolso real pendiente hasta ejecutarse.
- `FIN-25`: movimientos de apertura tipados incorporan deuda, credito administrado, garantia y liquidacion inicial sin simular caja del mes de adopcion.
- `FIN-25A`: deuda de apertura incrementa saldo pendiente; credito de apertura incrementa cobro disponible no aplicado; garantia de apertura incrementa fondos retenidos. Ninguno integra entrada o flujo de caja del mes.
- `FIN-25B`: deuda de apertura puede recibir aplicaciones como un cargo, pero no crea devengado; credito de apertura puede aplicarse o reembolsarse como una fuente, pero no crea entrada de caja de apertura.
- `FIN-25C`: `OpeningMovement` participa en `FinancialCorrection` y en las mismas invariantes de saldo que su obligacion o fuente equivalente.
- `FIN-26`: un contrato preexistente muestra vista previa y exige confirmacion del rango de cargos a generar; nunca hace backfill silencioso.
- `FIN-27`: pagos, aplicaciones, reembolsos, devoluciones y desembolsos confirmados no admiten fecha efectiva futura.
- `FIN-28`: un anticipo es un pago administrado con `AdvanceDesignation` a un origen futuro. No crea aplicacion, ingreso, snapshot patrimonial ni monto liquidable antes de `recognitionOn`.
- `FIN-28A`: el importe designado queda reservado y no puede aplicarse, reembolsarse ni suspender mora de otra deuda hasta liberarse o convertirse atomicamente.
- `FIN-29`: al reconocer el cargo, el sistema convierte atomicamente el anticipo designado en aplicacion hasta el importe disponible. Cancelar puede redirigirlo a penalidad o liberarlo para reembolso.
- `FIN-29A`: un cargo emitido con `recognitionOn` futuro se muestra como futuro, no integra devengado, deuda vencida ni liquidacion. En `recognitionOn` captura titularidad cuando corresponda y convierte anticipos bajo bloqueos de origen y periodo.
- `FIN-30`: todos los importes fuente son positivos y su efecto/signo deriva del tipo de movimiento.
- `FIN-31`: toda correccion de pago, reembolso, recuperacion, gasto pagado o desembolso usa `FinancialCorrection` y la matriz de efectos definida en 7.3.
- `FIN-32`: un movimiento real descubierto tarde crea un hecho ordinario con metadata `LateRecordedMovement`, no `FinancialCorrection`, cuando no existe un origen registrado que corregir.
- `FIN-32A`: el alta tardia exige fecha economica y evidencia del hecho original, `recordedAt` actual, motivo, clave idempotente y `accountingOn` en un periodo abierto no anterior; crea un solo hecho financiero, una metadata uno-a-uno y un solo efecto de caja.
- `FIN-32B`: si el periodo original puede reabrirse, no se usa alta tardia: el movimiento se registra normalmente en ese periodo.
- `FIN-32C`: aplicaciones posteriores de una fuente tardia usan su propia `appliedOn` abierta y respetan todas las invariantes ordinarias de fuente, deuda y atribucion.
- `FIN-32D`: el alta tardia admite entrada de pago o garantia, devolucion de proveedor, pago de gasto, reembolso, devolucion de garantia, desembolso y retorno. Conserva la entidad y enlaces ordinarios de ese tipo y revalida saldo, fuente, retenido y pagable antes de confirmar; si una dependencia posterior consumio el saldo, exige incluir primero su reversion o ajuste en la misma conciliacion atomica.
- `FIN-32E`: `LateRecordedMovement` no tiene importe ni deltas independientes, referencia exactamente un hecho ordinario y no puede existir mas de una metadata para ese hecho.

### 8.10 Depositos de garantia

- `DEP-01`: toda senia se clasifica antes de confirmar como anticipo de precio o garantia; nunca queda ambigua.
- `DEP-02`: una garantia se vincula a un solo contrato o reserva y se mantiene separada de ingreso y cargos.
- `DEP-03`: muestra acordado, varias recepciones, retenido, aplicaciones, reversiones, devoluciones y transferencias.
- `DEP-04`: cada recepcion registra pagador real, `receivedOn`, medio y referencia; aumenta caja y fondos retenidos, no ingreso.
- `DEP-05`: una garantia solo cubre cargos emitidos del mismo contrato o reserva de origen.
- `DEP-06`: aplicar crea atomicamente reduccion de garantia, fuente interna y aplicacion sin segunda entrada de caja.
- `DEP-07`: revertir parcial o totalmente restaura garantia, revierte aplicacion y neutraliza fuente interna en una transaccion.
- `DEP-08`: una retencion por dano, deuda, cancelacion o no-show exige cargo justificado del mismo origen.
- `DEP-09`: la devolucion permanece en borrador hasta la salida real, fija `returnedOn` y se paga siempre a la parte de facturacion.
- `DEP-10`: devolver reduce caja y fondos retenidos, no gasto.
- `DEP-11`: se permiten reposiciones mediante multiples recepciones.
- `DEP-12`: una renovacion con la misma parte de facturacion admite transferencia interna atomica sin mover caja.
- `DEP-13`: si cambia la parte de facturacion, se devuelve la garantia anterior y se recibe otra; no se transfiere.
- `DEP-14`: una garantia de apertura no crea entrada de caja actual.

### 8.11 Gastos

- `EXP-01`: un gasto pertenece inicialmente a una unidad o ubicacion y admite categoria, proveedor, descripcion, comprobantes y lineas.
- `EXP-02`: las lineas deben sumar exactamente el total materializado.
- `EXP-03`: el flujo lineal es planificado, pendiente de aprobacion, aprobado, incurrido y pagado.
- `EXP-03A`: planificado, pendiente o aprobado pueden cancelarse con motivo antes de incurrir; un gasto incurrido o pagado solo se corrige por el modelo hibrido.
- `EXP-04`: un rechazo conserva la version evaluada y crea una nueva version planificada para revisar y reenviar.
- `EXP-05`: solicitar aprobacion congela presupuesto, lineas, alcance, imputaciones, propietarios y documentos.
- `EXP-06`: cada presupuesto o gasto versionado se aprueba por separado; la incidencia solo resume.
- `EXP-07`: los umbrales se evaluan por cada imputacion materializada usando la politica mas especifica.
- `EXP-08`: un real menor o igual al aprobado continua; un exceso se bloquea salvo emergencia con permiso, motivo y evidencia.
- `EXP-09`: cambiar propietario, presupuesto, alcance o imputacion antes de incurrir invalida y exige nueva aprobacion.
- `EXP-10`: pasar a incurrido fija `incurredOn`; pasar a pagado fija `paidOn` y exige `paidOn >= incurredOn`.
- `EXP-11`: anticipos, cuotas y cuentas por pagar avanzadas a proveedores quedan fuera de V1.
- `EXP-12`: un gasto de ubicacion queda sin distribuir por defecto y aparece una sola vez en reportes de ubicacion/organizacion.
- `EXP-13`: puede imputarse a una unidad, seleccionadas o todas las activas en `allocatedOn`, guardando lineas concretas y redondeos.
- `EXP-14`: propietario y porcentaje se resuelven en `incurredOn`, aunque la imputacion se procese despues.
- `EXP-15`: un gasto pagado y atribuido tarde exige reabrir el origen o crear ajuste de atribucion en un periodo abierto elegido.
- `EXP-16`: una devolucion real de proveedor es `ExpenseRecovery` con `recoveredOn`; nunca reduce el gasto original y es la unica recuperacion sumada como tal.
- `EXP-17`: el traslado al inquilino es un `Charge` enlazado, no `ExpenseRecovery`; su aplicacion se cuenta una sola vez como cobro aplicado.
- `EXP-17A`: existe una sola identidad de traslado al inquilino por gasto, total o parcial.
- `EXP-18`: el traslado puede revisarse antes de emitir; despues cualquier diferencia usa ajuste enlazado, no otro traslado.
- `EXP-19`: gasto, devolucion de proveedor y cargo trasladado conservan referencias reciprocas para evitar doble recuperacion.

### 8.12 Incidencias y aprobaciones

- `MNT-01`: una incidencia incluye ubicacion o unidad, titulo, detalle, prioridad, reportante, responsable, fechas y adjuntos.
- `MNT-02`: el flujo usa comandos: abierta, evaluacion, pendiente de aprobacion, aprobada, en curso, resuelta, cerrada y cancelada.
- `MNT-03`: una resuelta puede volver a en curso con motivo; cerrada es terminal; cancelar no anula gastos existentes.
- `MNT-04`: una incidencia agrupa presupuestos, solicitudes y gastos, pero cada presupuesto versionado tiene aprobacion propia.
- `MNT-05`: politicas prevalecen unidad, ubicacion y organizacion, evaluadas por importe de cada imputacion.
- `MNT-06`: una parte propietaria emite un voto mediante cualquiera de sus representantes autorizados.
- `MNT-07`: todos los aprobadores de la version deben aceptar; rechazo crea revision planificada.
- `MNT-08`: si un aprobador pierde titularidad antes de incurrir, la solicitud se invalida y se envia a los nuevos propietarios.
- `MNT-08A`: la solicitud referencia la revision completa de `OwnershipDistribution` y se invalida ante cualquier cambio de partes o porcentajes aplicables, aunque sean las mismas partes.
- `MNT-09`: sin representante activo se resuelve el acceso o se usa emergencia; el equipo no vota en nombre del propietario.
- `MNT-10`: emergencia exige permiso, motivo y evidencia.
- `MNT-11`: edicion y voto usan version y bloqueo; una accion tardia recibe conflicto.
- `MNT-12`: propietarios y equipo reciben avisos de solicitud, decision, invalidacion y cambios relevantes.

### 8.13 Liquidaciones a propietarios

- `LIQ-01`: existe una identidad de liquidacion por propietario y periodo cerrado, con una sola revision vigente.
- `LIQ-02`: usa aplicaciones por `appliedOn`, reversiones por `reversedOn`, gastos por `paidOn`, devoluciones de proveedor por `recoveredOn` y ajustes por `accountingOn`.
- `LIQ-03`: cobros usan snapshot del cargo en `recognitionOn`; gastos y devoluciones de proveedor usan sus lineas materializadas.
- `LIQ-04`: cobros sin aplicar no aparecen en liquidaciones ni portales; garantias retenidas son informativas y no integran el neto.
- `LIQ-05`: fuentes compartidas se agregan para el propietario sin exponer pago, comprobante, otras aplicaciones ni detalle padre.
- `LIQ-06`: pases diarios son ingreso organizacional y nunca integran liquidaciones.
- `LIQ-07`: no se descuenta comision automatica; un honorario excepcional es un gasto separado.
- `LIQ-08`: la vista previa detecta fuentes duplicadas, gastos sin atribuir y movimientos pendientes.
- `LIQ-09`: confirmar crea una revision inmutable y conserva las anteriores bajo la misma identidad.
- `LIQ-10`: una fuente atribuida no puede integrar dos revisiones vigentes del mismo propietario.
- `LIQ-11`: neto cero o negativo queda informativo, no se arrastra, no crea deuda ni cobro al propietario.
- `LIQ-11A`: un ajuste positivo pagable al propietario integra el neto del periodo elegido. Un exceso ya desembolsado o un neto negativo se registra como informativo, no reduce automaticamente otra liquidacion ni crea cobro.
- `LIQ-12`: neto positivo admite varios `OwnerDisbursement` parciales hasta completar el total.
- `LIQ-13`: cada desembolso guarda `disbursedOn`, medio, referencia, comprobante y revision.
- `LIQ-13A`: saldo desembolsado neto es salidas confirmadas menos `OwnerFundReturn`; un retorno real vuelve a dejar ese importe pendiente de desembolso.
- `LIQ-13B`: cada `OwnerFundReturn` enlaza un solo desembolso confirmado, admite retornos parciales y exige `returnedOn >= disbursedOn`; la suma neta de retornos confirmados no supera ese desembolso.
- `LIQ-13C`: retorno y nuevo desembolso bloquean la misma revision y sus fuentes en orden determinista; en todo commit, desembolsado neto queda entre cero y el total pagable vigente.
- `LIQ-14`: con desembolsos parciales puede crearse una nueva revision si el total no queda debajo de lo ya pagado.
- `LIQ-15`: si el total corregido seria menor que lo pagado, se bloquea esa revision y la diferencia va como ajuste informativo a otro periodo abierto.
- `LIQ-16`: una liquidacion totalmente desembolsada no se edita; toda diferencia se registra como ajuste enlazado en otro periodo.
- `LIQ-16A`: una diferencia positiva puede aumentar el neto pagable del periodo elegido; una diferencia negativa que implicaria recuperar fondos ya desembolsados queda solo informativa.
- `LIQ-17`: una liquidacion de apertura representa saldo previo a favor sin inventar fuentes ni caja actual.
- `LIQ-18`: el propietario consulta solo sus revisiones visibles, totales autorizados y desembolsos.
- `LIQ-19`: pantalla y PDF proceden del mismo `ReportRun`.
- `LIQ-20`: si un desembolso confirmado nunca produjo salida real, `FinancialCorrection` neutraliza su caja registrada sin afirmar un nuevo movimiento real; si el dinero salio y regreso, `OwnerFundReturn` registra `returnedOn` sin editar la salida original.
- `LIQ-20A`: un retorno registrado sin entrada real se corrige mediante el tipo propio de `FinancialCorrection`; nunca se elimina ni se compensa creando otro desembolso ficticio.

### 8.14 Documentos y archivos

- `DOC-01`: se generan PDF de contratos, alojamiento, eventos, recibos, liquidaciones y reportes desde plantillas versionadas.
- `DOC-02`: cada version conserva datos resueltos, fuente, periodo efectivo, plantilla, checksum, autor y politica de retencion capturada.
- `DOC-03`: la audiencia se materializa por principal de negocio, por ejemplo `ownerPartyId`, no por representante; un grant futuro puede ejercer el historial elegible de esa parte.
- `DOC-04`: audiencia no basta. `TEAM` revalida membresia, rol y permiso; `PORTAL` revalida grant, capacidad y audiencia de la parte representada.
- `DOC-05`: solo usuarios autenticados descargan; V1 no envia documentos ni tokens de capacidad a partes sin cuenta.
- `DOC-06`: la descarga pasa por un endpoint autenticado que revalida cada solicitud y transmite el objeto; cualquier URL firmada interna de Spaces expira en cinco minutos y nunca se entrega como credencial reutilizable.
- `DOC-07`: contratos firmados, identificaciones, fotos, comprobantes y facturas externas pueden adjuntarse.
- `DOC-08`: V1 acepta PDF, JPEG, PNG y WebP; todo objeto pasa por cuarentena, firma binaria, checksum y antimalware.
- `DOC-09`: un archivo no validado o scanner no disponible permanece inaccesible.
- `DOC-10`: reemplazar crea una version nueva visible bajo la misma identidad documental.
- `DOC-11`: cada version captura su politica propia; `KEEP` es el valor inicial y un cambio solo se aplica a versiones creadas despues.
- `DOC-12`: cuando una version `DELETE_ON_REPLACE` sea reemplazada, se borra solo su binario; permanece la fila completa con metadata, audiencia, politica, checksum, evento, autor, fecha y tombstone. Una version `KEEP` nunca se borra por una politica posterior.
- `DOC-13`: cada acceso a documentos sensibles queda auditado.
- `DOC-14`: pantalla y PDF de un reporte consumen un `ReportRun` inmutable; el worker no vuelve a consultar datos actuales.
- `DOC-15`: cargas incompletas, temporales y no referenciadas se purgan y no se respaldan.

### 8.15 Notificaciones

- `NTF-01`: email se envia mediante Resend.
- `NTF-02`: WhatsApp usa un bridge HTTPS firmado, idempotente y administrado por plataforma.
- `NTF-03`: V1 envia solo mensajes operativos; marketing queda fuera.
- `NTF-04`: plantillas por organizacion y canal usan variables controladas.
- `NTF-05`: eventos incluyen vencimiento, mora, contrato, alojamiento, evento, aprobacion, incidencia y liquidacion.
- `NTF-06`: email y telefono actuales viven en `Party`, con historial append-only de valor, consentimiento, fuente y vigencia.
- `NTF-07`: consentimiento es por canal; valor nuevo comienza sin autorizacion.
- `NTF-08`: antes de cada intento se revalidan organizacion y destinatario. Para una `Party`, se validan version de contacto y consentimiento; para portal, tambien grant. Si cambia, se cancela sin redirigir.
- `NTF-09`: verificacion, invitacion y recuperacion de `User` son mensajes de seguridad separados del consentimiento operativo.
- `NTF-10`: una notificacion visible conserva un historial append-only de todos sus intentos y callbacks.
- `NTF-11`: estados son pendiente, pausado, procesando, enviado, entregado, resultado desconocido, fallido y cancelado.
- `NTF-12`: un fallo reintenta con espera creciente y limite; despues queda visible para reenvio manual.
- `NTF-13`: fallar o cancelar no revierte la operacion de negocio.
- `NTF-14`: el sobre congelado del bridge contiene solo ID opaco, destino y texto final. Timestamp anti-replay y firma van en encabezados y pueden cambiar sin alterar el payload idempotente.
- `NTF-14A`: reintentos automaticos reutilizan ID y sobre; un reenvio manual crea nueva revision e ID. Email exige clave estable del proveedor; si no puede deduplicar un timeout ambiguo queda en resultado desconocido para conciliacion manual.
- `NTF-15`: el bridge deduplica por ID; callbacks firmados son idempotentes y no modifican negocio.
- `NTF-16`: durante suspension, mensajes de negocio quedan pausados; callbacks tecnicos siguen aceptandose.

### 8.16 Importacion

- `IMP-01`: el usuario puede cargar ubicaciones, unidades y partes mediante formularios.
- `IMP-02`: debe existir una plantilla CSV separada para ubicaciones, unidades y partes.
- `IMP-03`: el original es temporal, privado, se elimina al terminar y nunca se respalda.
- `IMP-03A`: CSV usa un canal efimero separado de documentos, admite solo `text/csv` bajo limites de tamano/filas, parser estricto y sin descarga posterior.
- `IMP-04`: vista previa valida estructura, tipos, referencias, normalizacion, errores y advertencias por fila/campo.
- `IMP-05`: documento, RUC, email y telefono coincidentes son advertencias; codigos unicos y otras invariantes si bloquean.
- `IMP-06`: cada fila seleccionada es `CREATE_ONLY` o `LINK_EXPLICIT`; no existe upsert ni fusion automatica.
- `IMP-07`: el usuario corrige o excluye filas invalidas antes de confirmar; todas las filas seleccionadas se aplican en una transaccion o ninguna.
- `IMP-08`: confirmar revalida contra el estado actual y usa idempotencia; una vista previa obsoleta falla completa.
- `IMP-08A`: la vista previa persiste lote, hash, version, filas normalizadas, accion y target explicito de la misma organizacion; confirmar exige esa version y los lotes abandonados expiran por TTL.
- `IMP-08B`: filas normalizadas viven solo durante la vista previa y no se respaldan; al terminar se purgan y quedan hash, acciones, conteos, errores y referencias creadas/vinculadas.
- `IMP-09`: cada lote conserva procedencia y permite archivar atomicamente solo registros creados que no tengan nuevas referencias o cambios.
- `IMP-10`: importar contactos nunca infiere consentimiento.
- `IMP-11`: contratos y movimientos iniciales se cargan manualmente o mediante movimientos de apertura, no por CSV basico.

### 8.17 Auditoria

- `AUD-01`: se auditan accesos administrativos, denegaciones sensibles, permisos, grants, titularidades, modalidades, contratos, reservas, finanzas, periodos, importaciones, exportaciones y documentos.
- `AUD-02`: cada accion usa una allowlist de campos; PII se enmascara antes de persistir y nunca existe una copia cruda oculta.
- `AUD-03`: evento incluye organizacion, actor, modo, accion, entidad opaca, resultado, instante UTC, correlacion y cambios permitidos.
- `AUD-04`: nunca guarda contrasenas, sesiones, tokens, firmas, texto completo de mensajes, requests, responses, archivos ni secretos.
- `AUD-05`: los eventos son append-only e ineditables desde la aplicacion.
- `AUD-06`: usuarios con permiso buscan la auditoria de su organizacion mientras este activa.
- `AUD-07`: el superadministrador puede consultar siempre todos los eventos y campos ya persistidos y enmascarados de cualquier organizacion.
- `AUD-08`: esa excepcion no concede acceso a archivos ni endpoints de negocio y cada consulta queda auditada en plataforma.
- `AUD-09`: ver auditoria no concede permiso de exportarla.

## 9. Reportes y definiciones financieras

### 9.1 Dimensiones y filtros

Cada consulta crea un `ReportRun` inmutable con organizacion, creador, `accessMode`, `representedOwnerPartyId` cuando corresponda, audiencia, filtros, intervalo civil, `asOfAt`, revision, filas y totales. La pantalla renderiza ese resultado y el PDF usa el mismo identificador sin volver a consultar.

Los `calculationMode` son:

- `HISTORICAL_AS_OF`, predeterminado: reconstruye revisiones y movimientos conocidos al instante UTC `asOfAt` y conserva el periodo oficial de cada hecho.
- `CURRENT_RESTATED`: aplica las revisiones y correcciones hoy vigentes para explicar el resultado economico reformulado, sin modificar periodos ni liquidaciones.

Cuando corresponda, los filtros incluyen intervalo `[fromOn, toOn)`, mes, `asOfAt`, `calculationMode`, propietario, ubicacion, unidad, tipo fisico, modalidad, estado administrativo, estado operativo, parte de facturacion, pagador real, huesped, responsable, categoria, estado y criterio devengado o caja.

### 9.2 Definiciones

| Indicador | Calculo de V1 |
| --- | --- |
| Ingreso devengado | Cargos emitidos por `recognitionOn`, netos de revisiones y correcciones aplicables al modo. No se prorratea por interseccion. |
| Entrada de caja | Pagos administrados y recepciones de garantia por `receivedOn`, mas devoluciones de proveedor por `recoveredOn`. Excluye pagos directos a propietarios. |
| Cobro aplicado | Aplicaciones por `appliedOn`, incluidas garantias, menos reversiones por `reversedOn`. |
| Cobro no aplicado | Pagos administrados y credito de apertura al corte menos aplicaciones netas y reembolsos. Solo se muestra a nivel organizacion. |
| Saldo pendiente | Cargos vigentes reconocidos y deuda de apertura menos aplicaciones netas y ajustes al corte. |
| Gasto incurrido | Gastos por `incurredOn`, atribuidos o sin atribuir. Un gasto pagado sigue en su devengado original. |
| Gasto pagado | Gastos por `paidOn`; se presenta separado de gasto incurrido. |
| Recuperacion de proveedor | Entrada enlazada por `recoveredOn`; no reduce silenciosamente el gasto bruto. |
| Fondos retenidos | Garantias recibidas y de apertura menos aplicaciones, devoluciones y transferencias salientes, mas reversiones y transferencias entrantes. |
| Resultado devengado | Ingreso devengado menos gasto incurrido, sin garantias. |
| Resultado de caja atribuible | Cobro aplicado mas devolucion de proveedor atribuible menos gasto pagado atribuible. |
| Reembolso de pago | Salida por `refundedOn`; reduce caja, no gasto ni devengado. |
| Devolucion de garantia | Salida por `returnedOn`; reduce caja y fondos retenidos, no gasto. |
| Desembolso a propietario | Salida por `disbursedOn`; no constituye gasto. |
| Retorno de desembolso | Entrada por `returnedOn` que revierte caja de una salida real retornada; no es ingreso. |
| Flujo de caja registrado | Entradas administradas y retornos menos reembolsos, devoluciones, gastos pagados y desembolsos. Aplicaciones y transferencias internas no mueven caja. |
| Ocupacion de alojamiento | Noches ocupadas sobre noches comercializables; bloqueos se excluyen de numerador y denominador. |
| Ocupacion de eventos | Horas o franjas ocupadas sobre capacidad comercializable; no se combina con alojamiento. |

Una aplicacion posterior no mueve la entrada de caja original. Un pago puede ser entrada en agosto y cobro aplicado en septiembre sin duplicarse.

Cada indicador suma los deltas de `FinancialCorrection` que le correspondan, clasificados por `accountingOn`. El modo reformulado cambia la atribucion analitica, no el periodo oficial ni el delta de caja registrado.

Las fechas de la tabla rigen hechos registrados normalmente. Los efectos oficiales del hecho enlazado a `LateRecordedMovement` se agrupan por `accountingOn`; su fecha economica original se muestra aparte para explicar el atraso y nunca agrega una segunda fila de caja.

Alojamiento se reconoce completo en `checkInOn` y un evento completo en su fecha local de inicio. Un pase diario es ingreso de organizacion. La ocupacion si distribuye noches u horas por interseccion.

### 9.3 Reportes obligatorios

| Reporte | Regla temporal | Filtros minimos | Salida y agrupacion minima |
| --- | --- | --- | --- |
| Resumen ejecutivo | Cada indicador usa su fecha propia y el modo del run. | Propietario, ubicacion, unidad. | Sin filtro patrimonial muestra devengado, caja, aplicado, deuda, gastos, garantias y flujo; con filtro usa solo importes atribuibles. |
| Matriz mensual por unidad | `recognitionOn`, `appliedOn`, `incurredOn` y `paidOn`. | Propietario, ubicacion, modalidad, estados. | Una fila por unidad aunque tenga varias modalidades, con importes explicitos y sin cobros no aplicados. |
| Ingresos y egresos | Intervalo y criterio elegido. | Propietario, ubicacion, unidad, categoria. | A nivel organizacion incluye caja administrada; con dimension patrimonial usa cobros, devoluciones de proveedor y gastos atribuibles. |
| Estado de cuenta de parte | Cargos, aplicaciones, reversiones y corte. | Parte de facturacion, unidad, contrato o reserva. | Cronologia, pagador real cuando este autorizado, saldo administrado y deuda. |
| Morosidad | Saldo al fin de gracia y al corte. | Propietario, ubicacion, unidad, parte. | Regla congelada, pago oportuno sin aplicar, suspension, saldo y tramos de atraso. |
| Ocupacion contractual | Interseccion de contratos. | Propietario, ubicacion, unidad. | Dias contratados y comercializables. |
| Ocupacion de alojamiento | Noches civiles y bloqueos. | Propietario, ubicacion, unidad, estado. | Noches ocupadas, vacantes, bloqueadas y porcentaje comercializable. |
| Ocupacion de eventos | Fecha-hora, buffers y bloqueos. | Ubicacion, unidad, estado. | Horas o franjas ocupadas, comercializables y bloqueadas. |
| Alojamiento | Estadias y finanzas por sus fechas `On`. | Ubicacion, unidad, huesped, estado. | Noches, lineas tarifarias, reprogramacion, late checkout, cargos, cobro y saldo. |
| Eventos | Intervalos y fecha local de inicio. | Ubicacion, unidad, responsable, estado. | Paquete, asistentes, aforo, buffers, excesos, cargos y cobro. |
| Pases diarios | Franja y `recognitionOn`. | Ubicacion, categoria, estado. | Cantidades, cupo, ventas, cancelaciones y reembolsos identificados como ingreso organizacional. |
| Contratos | Estado al corte o eventos del intervalo. | Propietario, ubicacion, unidad, modalidad, estado. | Vigencia, ciclo, cuotas, adendas, canon, deuda y garantia. |
| Gastos | `incurredOn`, `paidOn` y `recoveredOn`. | Propietario, ubicacion, unidad, categoria, proveedor, aprobacion. | Version, lineas, imputacion, incurrido, pagado, devolucion de proveedor y cargo trasladado separados. |
| Garantias | Cada movimiento por su fecha `On`. | Ubicacion, unidad, parte, origen. | Acordado, multiples recepciones, retenido, aplicado, revertido, devuelto y transferido. |
| Liquidaciones | Periodo y revision. | Propietario, estado, ubicacion. | Importes atribuidos, ajustes, neto, desembolsos parciales y saldo, sin fuente compartida completa. |
| Bandeja organizacional | Existencia al corte. | Tipo, antiguedad, ubicacion y unidad. | Cobros sin aplicar, gastos sin atribuir, backfills y motivo de exclusion; no admite audiencia de propietario. |
| Movimientos de apertura | `openingOn` y `recordedAt`. | Tipo, parte, periodo, lote. | Deuda, credito, garantia y liquidacion inicial sin flujo actual. |
| Auditoria | Fecha/hora del evento dentro del rango. | Actor, accion, entidad. | Cronologia, correlacion y cambios autorizados, respetando ocultamiento de secretos. |

La interfaz puede aceptar fecha final inclusiva, pero normaliza el filtro a `[fromOn, toOn)` agregando un dia al extremo. Todo reporte muestra modo, corte, intervalo, zona y revision de calculo.

### 9.4 Reglas de presentacion

- Las etiquetas son siempre `Entrada de caja`, `Cobro aplicado`, `Gasto incurrido` y `Gasto pagado`; no se usa `Cobrado` o `Gastos` sin criterio.
- Una unidad activa debe aparecer en la matriz del periodo aunque este desocupada y tenga ingresos cero.
- Una unidad con varias modalidades aparece una sola vez y puede mostrar desglose.
- Un gasto de ubicacion sin distribuir debe aparecer una sola vez y nunca duplicarse al agrupar unidades.
- El reporte de propietario incluye solo movimientos atribuidos a ese propietario y su participacion.
- Entrada de caja, reembolsos y flujo registrado se muestran solo sin filtros patrimoniales.
- Al aplicar un filtro patrimonial, el sistema muestra Cobro aplicado, gastos atribuibles y resultado atribuible; no reparte pagos no aplicados de forma artificial.
- Cobros sin aplicar y pases diarios no aparecen en liquidaciones o reportes de propietario.
- Bloqueos se informan separados y se excluyen del denominador comercializable.
- Alojamiento y eventos nunca se combinan en un porcentaje unico de ocupacion.
- Una liquidacion negativa se rotula informativa y no como deuda del propietario.
- La vista reformulada identifica diferencias y `accountingOn` sin alterar el libro.
- Los totales PYG se presentan sin decimales y con separador local.
- Pantalla y PDF deben usar exactamente el mismo `ReportRun`.
- Los PDF grandes se generan de forma asincrona y quedan disponibles mediante enlace autorizado.

### 9.5 Caso de referencia aprobado

Para agosto, una consulta historica debe poder mostrar:

| Unidad | Ingreso devengado | Cobro aplicado | Pendiente | Gasto incurrido | Gasto pagado | Situacion |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| D1 | PYG 2.000.000 | PYG 2.000.000 | PYG 0 | PYG 70.000 | PYG 70.000 | Ocupada; plomeria y canilla detalladas. |
| D2 | PYG 0 | PYG 0 | PYG 0 | PYG 500.000 | PYG 0 | Desocupada; mantenimiento incurrido pendiente de pago. |

El mismo `ReportRun` produce esos totales en pantalla y PDF. Solicitar la vista reformulada crea otro run que identifica correcciones sin reescribir el resultado historico.

## 10. Flujos principales

### 10.1 Alta y cartera

1. El usuario verifica su email o acepta una invitacion.
2. Crea o ingresa a su organizacion en modo equipo.
3. Completa configuracion, feriados, horarios, buffers y catalogos.
4. Carga manualmente o importa ubicaciones, unidades y partes.
5. Define modalidades, vigencias, matriz de compatibilidad, titularidad y grants de propietarios.
6. El sistema valida porcentajes, codigos, advertencias de duplicados y compromisos antes de activar.

### 10.2 Contrato y cobro mensual

1. El operador crea un contrato en borrador para una unidad.
2. Agrega participantes, parte de facturacion, firma, vigencia, ciclo, vencimiento, cronograma, garantia y mora.
3. La API valida modalidad, compatibilidad, calendario, titularidad y activa el contrato.
4. Se materializan las ocurrencias futuras; el worker emite cada cargo al inicio del servicio.
5. Antes del cierre financiero, el operador revisa y cierra administrativamente cada cuota.
6. El operador registra un pago administrado con pagador real y comprobante.
7. El pago se aplica con `appliedOn`; se emite recibo y cualquier reversion queda enlazada.
8. Al terminar la gracia, la mora usa regla congelada y saldo historico; un pago oportuno sin aplicar suspende y alerta.
9. Adendas actualizan solo ocurrencias futuras; terminacion anticipada usa conciliacion guiada.
10. Reportes y portal separan devengado, entrada de caja, aplicado y deuda.

### 10.3 Alojamiento temporario

1. El operador consulta calendario, horarios y tarifas por noche.
2. Crea un alojamiento en borrador con parte de facturacion, huespedes, noches, senia tipada y extras.
3. El sistema materializa lineas por noche y cualquier ajuste al precio calculado.
4. Confirmar bloquea la unidad, revalida compatibilidad y genera cargos sin duplicados.
5. Se registran anticipo o garantia, check-in y check-out reales.
6. Autorizar late check-out crea revision y extiende el intervalo bajo bloqueo; la salida real guarda observacion y cargo adicional.
7. Reprogramacion, salida anticipada, cancelacion y no-show usan conciliacion guiada y preservan historia.
8. Reembolsos y devoluciones permanecen en borrador hasta que el dinero sale realmente.

### 10.4 Evento

1. El operador elige unidad, fecha-hora, responsables, asistentes y paquete.
2. El sistema aplica tipo de dia, aforo, buffers y ajuste de precio acordado.
3. Confirmar bloquea la unidad y valida matriz, intervalo y aforo.
4. El paquete puede revisarse hasta antes de check-in; despues, excesos generan cargos adicionales.
5. Si el evento supera su fin, se registra hora real, incidencia y cargo sin desplazar reservas posteriores.
6. Cancelacion, no-show y reprogramacion usan el mismo motor de conciliacion financiera.

### 10.5 Pase diario

1. El operador selecciona ubicacion, franja y cantidades por categoria.
2. Puede identificar comprador o responsable; solo sin ambos registra venta anonima.
3. La transaccion bloquea ubicacion/fecha, revalida franjas y cupo, y confirma pago total administrado.
4. El pase pasa a confirmado y luego usado al registrar ingreso.
5. Cancelar libera cupo; una venta identificada puede reembolsarse al ejecutar la salida.
6. Una venta anonima confirmada no admite reembolso; si el pase era futuro, reemplaza su cargo por penalidad reconocida y aplicada en `cancelledOn`.

### 10.6 Incidencia y gasto

1. El equipo registra una incidencia con evidencia.
2. Crea una version planificada de presupuesto, lineas e imputaciones.
3. El sistema evalua cada imputacion y solicita un voto por parte propietaria.
4. Un rechazo crea nueva version planificada; cambiar partes o porcentajes de titularidad invalida la aprobacion.
5. Antes de incurrir se revalidan presupuesto y propietarios; el exceso requiere emergencia justificada.
6. El gasto fija `incurredOn`, luego `paidOn`, y conserva imputaciones materializadas.
7. La devolucion de proveedor se registra como recuperacion; el traslado al inquilino es un cargo enlazado.

### 10.7 Liquidacion de propietario

1. El operador revisa cuotas, cobros sin aplicar, gastos sin atribuir y jobs del mes.
2. Cierra cuotas contractuales y luego el periodo bajo el bloqueo comun.
3. Selecciona propietario y periodo cerrado.
4. El sistema calcula aplicaciones, reversiones, gastos pagados, devoluciones de proveedor y ajustes por sus fechas `On`.
5. Confirmar crea una revision y un `ReportRun` comun para pantalla y PDF.
6. Un neto cero o negativo queda informativo; un neto positivo admite desembolsos parciales.
7. Una revision sobre pagos parciales no puede quedar debajo de lo ya desembolsado.
8. Una liquidacion totalmente desembolsada permanece fija y bloquea la reapertura del periodo.
9. Un retorno real se enlaza a su desembolso y rehabilita solo ese importe bajo el mismo bloqueo.
10. El propietario recibe aviso y consulta solo totales, revisiones y documentos autorizados.

## 11. Experiencia web

### 11.1 Navegacion del equipo

- Dashboard.
- Cartera.
- Personas y empresas.
- Contratos.
- Alojamiento, eventos y calendario.
- Pases diarios.
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
- Ocupacion de alojamiento y eventos como indicadores separados.
- Entradas, salidas, eventos y pases proximos.
- Contratos por finalizar.
- Trabajos asincronos o notificaciones fallidas que requieren atencion.

### 11.3 Portal de propietario

- Resumen de cartera y participaciones.
- Ocupacion y contratos permitidos.
- Ingresos, egresos y saldos por periodo.
- Incidencias y gastos pendientes de aprobacion.
- Liquidaciones y documentos descargables.
- Vista estrictamente de consulta fuera de las decisiones de aprobacion.
- Selector explicito de parte representada cuando un usuario representa a mas de una.
- Resumen contractual minimizado, sin PII ni fuentes financieras compartidas.

### 11.4 Contexto y suspension

- La interfaz muestra siempre organizacion y modo `TEAM` o `PORTAL`.
- Cambiar organizacion o modo invalida formularios pendientes del contexto anterior.
- Una organizacion suspendida no renderiza datos de negocio almacenados en cache.
- Al reactivar, un administrador revisa el plan de catch-up antes de ejecutar trabajos atrasados.

### 11.5 Adaptabilidad y accesibilidad

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
| Analisis de archivos | Scanner antimalware privado ejecutado por worker |
| Email | Resend |
| WhatsApp | Bridge HTTPS firmado, idempotente y administrado por plataforma |
| Zona horaria | `America/Asuncion` fija |

### 12.3 Estructura logica del monorepo

```text
apps/
  web/       Next.js, plataforma, equipo y portal de propietario
  api/       NestJS, REST, autenticacion y modulos de dominio
  worker/    Cargos, avisos, PDF, reintentos y tareas programadas
packages/
  contracts/ Esquemas Zod y contratos de intercambio compartidos
  config/    Configuracion comun de TypeScript, lint y herramientas
```

No se agrega un paquete compartido si solo tiene un consumidor. La logica de dominio permanece en el backend; compartir esquemas de entrada/salida no autoriza al frontend a reproducir reglas financieras.

### 12.4 Modulos NestJS

- `IdentityModule`.
- `PlatformAdministrationModule`.
- `OrganizationsModule`.
- `AuthorizationModule`.
- `PartiesModule`.
- `PortfolioModule`.
- `OwnershipModule`.
- `ContractsModule`.
- `BookingsModule`.
- `DayPassesModule`.
- `FinanceModule`.
- `MaintenanceModule`.
- `DocumentsModule`.
- `ImportsModule`.
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
- Toda respuesta autenticada usa cache privado y `no-store`.
- Las variables expuestas al navegador nunca contienen secretos.
- Formularios usan Zod y errores de API por campo, sin duplicar reglas de negocio complejas.
- Las rutas incluyen organizacion, `accessMode` y, en portal, `representedOwnerPartyId`; cada formulario envia `contextGeneration` y `expectedVersion`.
- Cambiar organizacion, modo o parte representada incrementa la generacion e invalida formularios abiertos del contexto anterior.

### 12.6 Persistencia PostgreSQL y Prisma

- Prisma es la via ordinaria de acceso a datos y migraciones.
- PostgreSQL debe mantener claves foraneas, indices, unicidad y restricciones de integridad.
- Operaciones monetarias, disponibilidad, titularidad y cierre usan transacciones.
- Agregados mutables usan una version monotona para concurrencia optimista.
- Disponibilidad, cupos, saldos, periodos y administradores usan bloqueos pesimistas en orden documentado.
- Toda mutacion bloquea la fila/version de estado de organizacion dentro de su transaccion y vuelve a exigir estado activo antes de confirmar.
- Contratos, alojamientos, eventos y bloqueos comparten el mismo punto de serializacion por unidad.
- Pases y revisiones de sus franjas comparten un punto de serializacion por ubicacion y fecha civil.
- Las restricciones por organizacion deben incluirse en claves compuestas relevantes.
- Indices deben cubrir `organizationId`, fechas, estados, unidad, propietario y claves de idempotencia usadas en filtros frecuentes.
- Las migraciones de produccion son versionadas, revisables y no se ejecutan implicitamente al arrancar la aplicacion.

### 12.7 Worker, cola y eventos

- V1 usa una cola persistida en PostgreSQL y no requiere Redis.
- La transaccion de negocio guarda tanto el cambio como un evento de salida.
- El worker reclama con `leaseOwner`, generacion de fencing, `leasedUntil` y heartbeat; otro worker recupera un lease vencido.
- Solo el propietario y generacion vigentes pueden confirmar resultado mediante compare-and-set; un worker con lease perdido no confirma.
- Los trabajos incluyen generacion de cargos, mora automatica, avisos, PDF y limpieza de artefactos temporales.
- Un trabajo deriva una clave estable de organizacion, origen, revision y efecto, y declara intentos y reintento.
- Antes de ejecutar, revalida fuente, organizacion, modo y autorizacion del solicitante cuando corresponda.
- La suspension pausa jobs de negocio sin consumir intentos; callbacks, limpieza, scanner y backups pueden continuar.
- `organization.statusVersion` actua como fencing: ningun efecto de negocio confirma despues del commit de suspension con una version anterior.
- Los fallos agotados quedan visibles para diagnostico y reejecucion autorizada.

### 12.8 Archivos

- La API autoriza cada carga y descarga.
- Los objetos usan claves no predecibles con prefijo logico por organizacion.
- Spaces permanece privado; no se guardan URL publicas permanentes.
- El checksum permite detectar cargas repetidas o corruptas.
- Los metadatos permanecen en PostgreSQL y el contenido binario en Spaces.
- Una carga inicia en cuarentena y no puede descargarse ni vincularse como disponible.
- V1 permite PDF, JPEG, PNG y WebP despues de validar tamano, firma real, parseo, checksum y antimalware.
- Si el scanner no esta disponible, el objeto permanece en cuarentena; no existe modo permisivo.
- CSV usa un canal efimero `text/csv` separado, con parser y limites propios, sin convertirse en documento descargable.
- Cargas incompletas, CSV procesados y temporales se purgan y no se respaldan.
- Cada descarga sensible pasa por endpoint autenticado, se audita y usa una URL interna firmada de maximo cinco minutos.

### 12.9 Reportes y artefactos

- `ReportRun` guarda creador, `accessMode`, parte representada, audiencia, `calculationMode`, filtros, `asOfAt`, revision, filas y totales.
- Pantalla, PDF y futuras exportaciones consumen el mismo resultado.
- Solicitar exportacion exige permiso separado de lectura.
- El PDF usa una clave estable derivada del run, plantilla y renderizador; reintentar reutiliza el artefacto logico.
- Generar y descargar revalidan autorizacion; un artefacto no incorpora acceso permanente.

## 13. API y flujo de datos

### 13.1 API REST

- Prefijo inicial `/api/v1`.
- Rutas de negocio usan `/organizations/:organizationId/team/...` o `/organizations/:organizationId/portal/:representedOwnerPartyId/...`; plataforma usa `/platform/...`.
- OpenAPI es parte del contrato entregable.
- Las entradas y salidas usan esquemas Zod estables.
- Listados usan paginacion, orden y filtros explicitos.
- Las transiciones usan comandos explicitos como `/commands/confirm`; no se permite `PATCH status` generico.
- Todo comando repetible exige `Idempotency-Key`; todo agregado existente exige `expectedVersion`.
- La clave se limita por principal, organizacion o scope de onboarding/plataforma, `accessMode`, parte representada, ruta objetivo y comando; guarda hash canonico.
- Repetir clave y payload reproduce el resultado; otro payload devuelve `409 IDEMPOTENCY_KEY_REUSED`.
- Tras autenticar y autorizar, un replay idempotente se resuelve antes de comparar `expectedVersion`; la huella minima de una clave usada no se reutiliza.
- Los recursos nunca confian en un `organizationId` enviado por el cliente para autorizar acceso.
- Cambios incompatibles requieren una nueva version de API.

### 13.2 Flujo de una mutacion

1. Next.js envia la solicitud autenticada.
2. NestJS asigna identificador de correlacion.
3. La ruta resuelve organizacion, `accessMode` y parte representada; el backend revalida usuario, membresia o grant y estado.
4. Zod valida estructura y tipos.
5. Tras autorizar, se valida `Idempotency-Key` y hash; un replay exacto retorna su resultado aunque la generacion haya cambiado.
6. Una operacion nueva valida `contextGeneration` y `expectedVersion`, adquiere bloqueos deterministas y valida negocio.
7. La transaccion bloquea/revalida el estado de organizacion y guarda dominio, version, auditoria, idempotencia y outbox.
8. La API responde con estado y version nuevos.
9. El worker revalida y procesa efectos secundarios sin reabrir la transaccion original.

### 13.3 Flujo de reporte

1. El usuario define filtros y criterio financiero.
2. La API valida alcance y crea un `ReportRun` con creador, acceso, audiencia, calculo y `asOfAt`.
3. La pantalla recibe el run, datos y metadatos.
4. Solicitar PDF es un comando separado con permiso de exportacion y referencia el mismo run.
5. El worker genera desde ese snapshot y una clave estable.
6. La descarga revalida autorizacion y queda auditada.

## 14. Seguridad

### 14.1 Autenticacion y sesion

- Contrasenas con hash resistente y parametros revisables.
- Cookies de sesion `HttpOnly`, `Secure` y `SameSite` apropiado.
- Proteccion CSRF u origen estricto para solicitudes que modifican datos.
- Verificacion de email y tokens de recuperacion de un solo uso con expiracion.
- Rate limiting para login, recuperacion, invitaciones y endpoints sensibles.
- CORS restringido a origenes configurados.
- Una invitacion solo puede aceptarla el `User` con el email verificado invitado.
- Los mensajes de verificacion, invitacion y recuperacion son seguridad de `User`, separados del consentimiento operativo de `Party`.
- Cambiar o recuperar credenciales rota identificadores de sesion y revoca las sesiones anteriores.
- Superadministradores usan MFA; suspension, recuperacion administrativa y acceso sensible de plataforma exigen reautenticacion reciente.
- El bootstrap y recuperacion del primer superadministrador se documentan como procedimiento fuera de banda auditado.

### 14.2 Autorizacion

- Denegar por defecto cuando no existe permiso explicito.
- Verificar permiso y alcance en el backend, incluso si la interfaz oculta la accion.
- Separar permisos de plataforma, organizacion y portal de propietario.
- Organizacion y modo proceden de la ruta; roles de equipo y grants de portal nunca se unen.
- Una revocacion afecta la siguiente solicitud, job y descarga.
- Nadie puede conceder permisos que no posee ni dejar cero administradores efectivos.
- El superadministrador puede consultar la auditoria persistida y enmascarada, pero no obtiene acceso implicito a negocio o archivos.
- Exigir permisos reforzados para anulaciones, reaperturas, titularidades y exportacion de datos sensibles.
- Auditar elevaciones y cambios de acceso.

### 14.3 Proteccion de datos

- HTTPS obligatorio fuera de desarrollo local.
- Secretos fuera del repositorio y rotables.
- Base, respaldos y objetos cifrados en reposo mediante capacidades del proveedor.
- Descargas mediante endpoint autenticado; URLs firmadas internas y breves nunca sustituyen la sesion.
- Logs sin contrasenas, tokens, documentos, RUC completos innecesarios ni contenido financiero sensible.
- Datos de una organizacion suspendida se conservan, pero no quedan accesibles a sus miembros.
- La auditoria usa allowlists por accion y enmascara PII antes de persistirla.
- Solo la historia funcional necesaria se conserva indefinidamente; temporales y objetos sin referencia se eliminan.
- Tombstones de contenido purgado se respaldan y vuelven a aplicarse tras una restauracion para no resucitar binarios eliminados.
- Una organizacion suspendida bloquea tambien portal, invitaciones, reportes, descargas y exportaciones.

## 15. Manejo de errores y resiliencia

### 15.1 Contrato de error

```json
{
  "code": "BOOKING_OVERLAP",
  "message": "La unidad ya tiene una reserva o bloqueo para esas fechas.",
  "fieldErrors": {
    "checkInOn": ["El intervalo entra en conflicto con una reserva confirmada."]
  },
  "correlationId": "identificador-seguro"
}
```

- `400` para solicitud mal formada.
- `401` para sesion ausente o invalida.
- `403` para permiso o alcance insuficiente.
- `404` para recurso inexistente dentro del alcance autorizado.
- `409` para conflicto de negocio o concurrencia.
- `410` para contenido purgado cuya metadata historica permanece.
- `413` para archivo o solicitud demasiado grande.
- `415` para tipo de archivo no permitido.
- `422` para validacion semantica por campos.
- `429` para limite de solicitudes.
- `503` para dependencia temporalmente no disponible.

### 15.2 Reglas de resiliencia

- Los mensajes al usuario deben explicar la accion posible sin exponer detalles internos.
- Un error de Resend, WhatsApp o Spaces no revierte movimientos financieros confirmados.
- Los efectos externos se reintentan desde la cola persistida.
- Las operaciones concurrentes de reservas, pagos y cierres deben detectar conflictos y responder sin corrupcion.
- El mismo bloqueo protege carreras alojamiento-evento-contrato-bloqueo y el mismo cupo protege pases concurrentes.
- Un worker confirma mediante compare-and-set de `leaseOwner` y generacion de fencing; un lease perdido no puede confirmar.
- Antes de un efecto externo irreversible, el worker bloquea la version de estado de organizacion y registra el despacho. Suspender usa el mismo punto de serializacion: ningun despacho nuevo comienza despues de su commit.
- Un efecto aceptado por un proveedor antes de la suspension no se deshace; sus callbacks tecnicos siguen registrandose.
- Un timeout externo no se interpreta como exito; el bridge deduplica por ID opaco estable.
- Contacto o consentimiento cambiados cancelan el mensaje pendiente en vez de redirigirlo.
- Un scanner no disponible mantiene el archivo en cuarentena.
- Toda respuesta inesperada se registra con correlacion y se presenta como un mensaje seguro.
- Los trabajos fallidos y movimientos que requieren intervencion deben aparecer en una bandeja operativa.
- Reactivar muestra un plan de catch-up; no ejecuta automaticamente todo el atraso ni envia recordatorios obsoletos.

## 16. Requisitos no funcionales

### 16.1 Escala y rendimiento

- Hasta 1.000 unidades por organizacion.
- Decenas de usuarios concurrentes por organizacion.
- Miles de movimientos mensuales por organizacion.
- Miles de alojamientos, eventos y pases mensuales, con picos concurrentes sobre una unidad o franja.
- Consultas habituales con objetivo `p95 <= 2 s` bajo la carga de referencia.
- Reportes simples con objetivo `p95 <= 5 s`.
- Reportes pesados y PDF procesados en segundo plano sin bloquear la interfaz.
- Listados, calendarios y pases paginados o virtualizados; no se cargan carteras completas sin limite.

La carga de referencia se versiona como escenario reproducible y usa:

- Una organizacion sembrada deterministicamente con 1.000 unidades, 24 meses, 20.000 ocurrencias contractuales, 100.000 movimientos financieros confirmados, 10.000 alojamientos/eventos y 50.000 pases.
- Cincuenta sesiones virtuales concurrentes durante cinco minutos de calentamiento y veinte minutos medidos, con mezcla fija de 60 % consultas habituales, 25 % comandos financieros/de cartera, 10 % calendario/cupo y 5 % reportes simples.
- Tres ejecuciones consecutivas sobre imagenes y seeds con checksum. El manifiesto de referencia fija dos replicas API de 1 vCPU/2 GiB, dos workers de 1 vCPU/2 GiB y PostgreSQL de 4 vCPU/8 GiB sobre SSD local; pool, SO, imagenes y versiones quedan registrados junto al resultado.
- Los umbrales `p95` deben cumplirse en cada ejecucion, con menos de 0,1 % de errores inesperados y cero violaciones de aislamiento, dinero, cupo o idempotencia. Conflictos `409` previstos por la carga no cuentan como error.
- Los reportes pesados se solicitan durante la misma prueba: la API debe aceptarlos dentro del objetivo habitual, procesarlos en background y dejar registrada su latencia de cola y ejecucion, sin imponerles el umbral de reportes simples.

### 16.2 Disponibilidad operativa

- Health checks separados para web, API, worker, base y dependencias externas.
- Degradacion controlada: una caida de notificaciones no impide registrar cobros o gastos.
- Los trabajos pendientes sobreviven reinicios del worker.
- Las operaciones criticas usan transacciones y claves de idempotencia.
- Leases vencidos se recuperan sin repetir efectos confirmados.
- La suspension pausa negocio por organizacion y la reactivacion ejecuta un catch-up controlado.

### 16.3 Respaldo y recuperacion

- Respaldo cifrado diario de PostgreSQL con retencion minima de 30 dias.
- Versionado o politica de recuperacion equivalente para archivos necesarios.
- Prueba documentada de restauracion al menos una vez por trimestre.
- La restauracion debe verificar base, objetos durables, auditoria, outbox, idempotencia y `ReportRun`.
- Cuarentena, CSV originales, cargas incompletas y temporales no se respaldan.
- La restauracion reaplica tombstones y purgas documentales; un binario eliminado no vuelve a estar disponible aunque exista en un respaldo aun retenido.

### 16.4 Observabilidad

- Logs estructurados con servicio, organizacion anonimizada cuando corresponda, usuario, ruta y correlacion.
- Metricas de latencia, errores, conexiones, trabajos, reintentos y proveedores externos.
- Metricas de conflictos, deadlocks, cupos, leases, cuarentena y mensajes pausados.
- Alertas para errores sostenidos, cola o lease detenidos, respaldos fallidos y almacenamiento no disponible.
- Auditoria funcional separada de logs tecnicos.

### 16.5 Compatibilidad y accesibilidad

- Soporte para las dos versiones estables mas recientes de Chrome, Edge, Firefox y Safari al momento de cada entrega.
- Diseno adaptable desde 360 px.
- WCAG 2.2 AA en autenticacion, cartera, cobros, reservas, gastos, liquidaciones y reportes.
- Formato local de fecha y PYG consistente en toda la interfaz y documentos.
- V1 usa exclusivamente `America/Asuncion`; la API rechaza otra zona y el despliegue registra version de tzdata.
- Los objetivos de accesibilidad incluyen alojamiento, eventos, pases, documentos y seleccion explicita de modo.

## 17. Estrategia de pruebas

### 17.1 Pruebas unitarias

- Distribuciones atomicas, porcentajes de cuatro decimales y redondeo materializado.
- Intervalos semiabiertos, modalidades simultaneas y matriz por unidad.
- Ciclos calendario/aniversario, ancla de fin de mes, ocurrencias, adendas y cierres de cuota.
- Mora con regla congelada, worker tardio y cobro oportuno sin aplicar.
- Revisiones financieras, reversiones parciales y movimientos de apertura.
- Matriz completa de efectos correctivos, incluida reversion total y parcial por cada tipo.
- Alta tardia de cada entrada y salida soportada, reembolso de credito de apertura y limites de `OwnerFundReturn`.
- Garantias con multiples recepciones, aplicacion/reversion compuesta y transferencia a renovacion.
- Gastos lineales, aprobaciones por presupuesto, devoluciones de proveedor y traslado unico.
- Liquidaciones negativas informativas, revisiones restringidas y desembolsos parciales.
- Tarifas por noche, feriados, paquetes, aforo, buffers y cupos de pases.
- Franjas semiabiertas no solapadas, venta con solo responsable y penalidad anonima previa al pase.
- Modos historico/reformulado y checksum de `ReportRun`.
- Transiciones de contrato, alojamiento, evento, pase, gasto e incidencia.

### 17.2 Pruebas de integracion

- PostgreSQL real ejecutado en Docker.
- Claves foraneas, unicidad y restricciones compuestas.
- Transacciones y bloqueos de pagos, reversiones, garantias, liquidaciones y periodos.
- Concurrencia mixta de contrato, alojamiento, evento y bloqueo para una unidad.
- Concurrencia de cupo de pases por ubicacion y fecha, incluida revision de franja y dos IDs que intentan solaparse.
- Carreras entre retorno y desembolso, y entre dos retornos parciales de la misma salida.
- Alta tardia de entradas y salidas sobre periodo no reabrible, con un solo efecto de caja en `accountingOn` y conciliacion de dependencias consumidas.
- Reclamo concurrente, heartbeat y recuperacion de leases.
- Aislamiento de organizaciones en lecturas y escrituras.
- Suspension, pausa y catch-up por organizacion.
- Importacion CSV atomica y rollback por archivado controlado.
- Persistencia inmutable de `ReportRun` y PDF con clave estable.
- Migraciones reproducibles desde una base vacia y validacion de cada migracion nueva sobre el estado anterior del esquema en desarrollo.
- Almacenamiento compatible con Spaces y scanner antimalware simulados.

### 17.3 Pruebas de contrato y API

- Entradas y respuestas contra esquemas Zod.
- Documento OpenAPI actualizado.
- Codigos de error estables.
- Paginacion, filtros y orden.
- Comandos explicitos, `expectedVersion` e idempotencia con mismo/distinto payload.
- Organizacion por ruta, modo explicito, contexto obsoleto y revocacion inmediata.
- Autenticacion, permisos, grants, alcance historico y exportacion separada.
- Rechazo de zonas distintas de `America/Asuncion`.

### 17.4 Pruebas de extremo a extremo

- Autorregistro, verificacion y creacion de organizacion.
- Cambio de organizacion y modo con formularios abiertos.
- Importacion CSV todo-o-nada y archivo controlado del lote.
- Cartera con modalidades simultaneas, matriz y copropiedad.
- Contrato, ocurrencias, cierre de cuota, adenda, mora, pago y terminacion.
- Alojamiento con noches, feriado, reprogramacion, late checkout y cancelacion.
- Evento por hora con paquete, aforo, buffer, exceso e incidencia.
- Pase con comprador, solo responsable y anonimo, pago total, cupo, uso, cancelacion, penalidad y regla de reembolso.
- Incidencia, aprobacion, gasto, devolucion de proveedor y traslado al inquilino.
- Garantia recibida, aplicada, revertida, transferida y devuelta.
- Liquidacion, revision sobre pago parcial, neto negativo, PDF y desembolsos parciales.
- Cada modo historico o reformulado crea su propio `ReportRun`; pantalla y PDF de ese modo comparten el run.
- Restricciones y minimizacion del portal de propietario.

### 17.5 Pruebas de seguridad y regresion obligatorias

- Intentar acceder a cada recurso con un usuario de otra organizacion.
- Intentar elevar permisos manipulando solicitudes del navegador.
- Intentar operar desde una pestana con organizacion o modo obsoleto.
- Verificar que superadmin pueda consultar auditoria enmascarada, pero no datos ni archivos de negocio.
- Reejecutar jobs de cuotas, cargos, mora, PDF y avisos.
- Enviar confirmaciones incompatibles concurrentes entre contrato, alojamiento, evento y bloqueo.
- Modificar titularidad y modalidad despues de periodos confirmados.
- Anular y reabrir movimientos con y sin permiso.
- Verificar que depositos nunca aparezcan como ingreso.
- Verificar que un gasto de ubicacion no se duplique al consolidar unidades.
- Verificar que alojamiento y evento que cruzan mes se reconocen completos una sola vez.
- Verificar que un reembolso reduce caja sin crear gasto ni borrar la recepcion original.
- Retirar consentimiento antes de un reintento y comprobar la cancelacion.
- Cargar MIME falso, malware y archivo truncado y comprobar cuarentena sin descarga.

### 17.6 Casos frontera obligatorios

| ID | Escenario | Resultado esperado |
| --- | --- | --- |
| `BND-01` | Contrato anclado al 31 atraviesa febrero. | Usa ultimo dia de febrero y recupera el 31 sin deriva. |
| `BND-02` | Contrato firmado el 31-ene inicia 1-feb. | Firma y vigencia permanecen separadas. |
| `BND-03` | Contrato termina 31-ago y otro inicia 1-sep. | Intervalos contiguos no se superponen. |
| `BND-04` | Evento 15:00 a 03:00 del dia siguiente. | Fecha-hora explicita, UTC resuelto y reconocimiento completo en fecha de inicio. |
| `BND-05` | Evento termina 13:00 y otro inicia 13:00 con buffer. | Se rechaza hasta terminar el buffer configurado. |
| `BND-06` | Dos modalidades distintas coinciden. | Solo se permite si la matriz de esa unidad autoriza el par. |
| `BND-07` | Alojamiento y evento incompatibles se confirman a la vez. | Solo uno confirma; el otro recibe `409` sin efectos huerfanos. |
| `BND-08` | Pago suficiente recibido antes de gracia queda sin aplicar. | Suspende mora, reserva virtualmente el saldo una vez y genera alerta. |
| `BND-09` | Worker de mora corre tarde. | Usa saldo existente al fin de gracia y regla congelada. |
| `BND-10` | Cierre compite con movimiento del mismo mes. | El bloqueo de periodo serializa y evita registro parcial. |
| `BND-11` | Se revierte parte de una aplicacion de garantia. | Restaura deuda y retenido, neutraliza la fuente interna y no mueve caja. |
| `BND-12` | Liquidacion parcialmente desembolsada se revisa. | Nuevo total no baja de lo desembolsado; en caso contrario se bloquea. |
| `BND-13` | Una liquidacion esta totalmente desembolsada. | El periodo no reabre y la correccion va a un periodo abierto elegido. |
| `BND-14` | Se crea PDF y luego cambia un movimiento. | Pantalla y PDF del run original no cambian; un nuevo run refleja la mutacion. |
| `BND-15` | Bridge acepta mensaje y luego hace timeout. | Reintenta con el mismo ID opaco y el bridge deduplica. |
| `BND-16` | Organizacion suspendida acumula cuotas. | No procesa negocio; al reactivar muestra catch-up y no envia avisos obsoletos. |
| `BND-17` | Dos ventas compiten por el ultimo cupo de pase. | Una confirma cupo y pago; la otra no consume ninguno. |
| `BND-18` | Pase anonimo confirmado se cancela. | Libera cupo y no admite reembolso. |
| `BND-19` | CSV seleccionado tiene un conflicto al confirmar. | Inserta cero filas y exige nueva vista previa. |
| `BND-20` | Superadmin sin membresia consulta auditoria. | Accede a eventos ya enmascarados, queda auditado y no accede a negocio. |
| `BND-21` | Documento se reemplaza bajo politica de eliminacion. | Borra contenido anterior y conserva evento, autor, fecha y checksum. |
| `BND-22` | Contrato visible hasta 31-jul. | Conserva `agreedEndsOn=31-jul` y calendario exclusivo hasta 1-ago. |
| `BND-23` | Dos modalidades compatibles coinciden. | Ambas confirmaciones pueden persistir; la misma pareja en otra unidad sin regla se deniega. |
| `BND-24` | Cuota cerrada sigue impaga. | Importe/detalle quedan fijos, pero deuda, aplicaciones y mora continuan; una cuota abierta bloquea el periodo. |
| `BND-25` | Finalizacion natural auto y manual. | Auto finaliza; manual queda activo/vencido, pero ambos liberan calendario en `effectiveUntilOn`. |
| `BND-26` | Adenda cae dentro de una cuota futura. | Exige division explicita sin prorrateo automatico y marca la ocurrencia anterior reemplazada. |
| `BND-27` | Pase se confirma y luego se usa. | Pase, cargo, pago y aplicacion/anticipo son atomicos; usado es terminal y no se cancela. |
| `BND-28` | Dos distribuciones compiten o cambian porcentajes. | Solo una revision completa confirma, ningun cargo se emite sin cobertura y toda aprobacion ligada a la revision anterior se invalida. |
| `BND-29` | Grant se revoca con descarga iniciada. | El endpoint autenticado deniega la siguiente solicitud; una URL interna nunca funciona como credencial del usuario. |
| `BND-30` | Version `KEEP`, cambio a `DELETE`, nuevo reemplazo. | La version `KEEP` se conserva; solo una version que capturo `DELETE_ON_REPLACE` puede purgarse. |
| `BND-31` | Lease vence y la organizacion se suspende durante despacho. | Fencing impide confirmar al worker viejo y ningun despacho nuevo comienza despues del commit de suspension. |
| `BND-32` | Se notifica a un inquilino sin grant de portal. | Valida contacto y consentimiento, no exige grant; una notificacion de portal si lo exige. |
| `BND-33` | CSV temporal finaliza o expira. | Confirma exactamente el lote versionado o falla completo; elimina el original y no lo restaura desde backup. |
| `BND-34` | Se reintenta el comando que cambio contexto. | La misma clave/payload reproduce el resultado aunque `contextGeneration` ya haya aumentado. |
| `BND-35` | Descarga en `TEAM` y `PORTAL`. | Equipo valida membresia/permiso; portal grant/audiencia; logout, suspension o falta de sesion deniegan y la URL interna no se reutiliza. |
| `BND-36` | Superadmin tambien es miembro. | MFA y reautenticacion protegen plataforma; `PLATFORM` y `TEAM` no unen privilegios. |
| `BND-37` | CSV coincide por RUC o email. | Muestra advertencia; `CREATE_ONLY` crea y `LINK_EXPLICIT` exige target de la misma organizacion sin actualizarlo. |
| `BND-38` | Email aceptado con respuesta perdida. | Si no hay deduplicacion verificable queda resultado desconocido y no se reintenta automaticamente. |
| `BND-39` | Usuario recupera contrasena. | Rota la sesion y revoca cookies anteriores antes de permitir operaciones sensibles. |
| `BND-40` | Late checkout compite con otra confirmacion. | La extension toma bloqueo y solo confirma si el nuevo `calendarEndsAt` respeta limpieza y compromiso siguiente. |
| `BND-41` | Paquete de evento cambia antes de check-in. | Crea revision, conserva la anterior, revalida aforo/calendario y corrige el cargo sin editar en sitio. |
| `BND-42` | Se descubre un pago real cuyo mes tiene liquidacion totalmente desembolsada. | Crea un solo pago y su metadata tardia con fecha real y `recordedAt` actual; caja oficial ocurre una vez en `accountingOn` abierto y el periodo original no cambia. |
| `BND-43` | Se reembolsa un credito de apertura. | Reduce una vez la fuente y la caja actual, sin inventar entrada de apertura, ingreso ni gasto. |
| `BND-44` | Dos retornos compiten por el mismo desembolso. | El bloqueo limita la suma al desembolso, nunca deja neto negativo y solo el retorno confirmado rehabilita saldo pagable. |
| `BND-45` | Un pase tiene responsable pero no comprador. | Es identificado, usa al responsable como parte de facturacion y sigue conciliacion/reembolso identificado. |
| `BND-46` | Pase anonimo futuro se cancela antes de su fecha. | Reemplaza cargo futuro por penalidad en `cancelledOn`, aplica anticipo ese dia, libera cupo y no crea reembolso ni aplicacion futura. |
| `BND-47` | Dos franjas distintas intentan solaparse o vender durante la revision. | El bloqueo por ubicacion/fecha confirma una configuracion o venta valida y rechaza la otra sin sobreventa. |
| `BND-48` | Se revierte total o parcialmente cada tipo de la matriz financiera. | Cada dimension produce solo su delta permitido; una reversion total cuadra con el origen sin doble caja. |
| `BND-49` | Se descubre un reembolso real omitido cuya fuente fue consumida despues. | Exige conciliar dependencias atomicamente y registra una sola salida en `accountingOn`, sin saldo negativo ni cambio del periodo original. |

## 18. Criterios de aceptacion de V1

### 18.1 Plataforma, contexto y acceso

- Una organizacion opera solo en PYG y `America/Asuncion`; API e interfaz rechazan otra zona.
- Un usuario de A no descubre ni modifica recursos validos de B.
- Una mutacion desde una pestana con contexto obsoleto falla antes de ejecutar reglas o escrituras de dominio.
- El usuario que es equipo y representante debe elegir modo; sus permisos no se combinan.
- Revocar membresia o grant impide la siguiente solicitud, job y descarga.
- El superadministrador consulta auditoria enmascarada sin membresia, pero no negocio ni archivos.
- Una organizacion suspendida bloquea todo acceso de negocio y al reactivar exige revisar catch-up.

### 18.2 Cartera, modalidades y titularidad

- Se crea U1 con diez unidades, nombres editables y tipos fisicos.
- Una unidad puede habilitar alojamiento y eventos simultaneamente con vigencias independientes.
- Una coincidencia entre modalidades solo se permite si la matriz de esa unidad la autoriza.
- Estado administrativo y operativo aparecen separados y el calendario prevalece.
- Una distribucion de copropiedad se confirma atomicamente y suma `100.0000 %`.
- Cambiar propietarios en septiembre no modifica snapshots ni liquidaciones de agosto.
- D7 puede marcarse en venta y continuar alquilada.

### 18.3 Contratos, cuotas y mora

- Firma 31-ene y vigencia 1-feb a 31-jul se guardan por separado.
- Cada contrato elige mes calendario o aniversario y previsualiza todas sus ocurrencias.
- Un ancla 31 usa ultimo dia de febrero y vuelve al 31 cuando existe.
- Activar materializa cuotas futuras y cada cargo se emite una sola vez al inicio.
- Todas las cuotas del mes se cierran administrativamente antes del cierre financiero; su deuda y mora siguen vigentes.
- Una adenda cambia PYG 1.000.000 a PYG 1.300.000 solo desde su fecha efectiva y no altera cargos emitidos.
- Una terminacion 15-abr conserva `agreedEndsOn` 31-jul, corta disponibilidad el 16-abr y usa conciliacion manual del cargo vigente.
- La regla de mora se congela al emitir y un worker tardio usa saldo al fin de gracia.
- Un cobro suficiente recibido a tiempo sin aplicar suspende mora y genera alerta.

### 18.4 Caja administrada y correcciones

- Solo fondos administrados aparecen en caja; un pago directo al propietario permanece fuera y la deuda solo se cancela si despues existe una recepcion real por la organizacion.
- Parte de facturacion y pagador real se guardan separados.
- Un pago recibido en agosto y aplicado en septiembre aparece como entrada en agosto y aplicado en septiembre.
- Una correccion sin dependencias en periodo abierto crea revision; con dependencias o cierre crea contramovimiento.
- Una reversion parcial libera exactamente su importe sin modificar la aplicacion original.
- Un reembolso exige beneficiario explicito y solo se confirma al salir el dinero.
- Movimientos de apertura incorporan deuda, credito y garantia sin caja ficticia; una liquidacion de apertura representa saldo previo del propietario.
- Un credito de apertura se aplica o reembolsa bajo el mismo limite de fuente; reembolsarlo crea solo la salida actual.
- Un hecho real omitido en un periodo no reabrible conserva su fecha real, se registra una vez en `accountingOn` abierto y no reescribe el cierre.
- Cada tipo correctivo cumple la matriz de devengado, deuda, caja, retenido y propietario en reversiones parciales y totales.

### 18.5 Alojamiento temporario

- Una estadia materializa una linea por noche y congela feriado, tarifa, ajuste y horarios aplicados.
- La tarifa calculada puede cambiar mediante descuento o recargo explicito con motivo.
- Check-in/out y buffers usan valores de organizacion con reemplazos de unidad.
- Autorizar late check-out extiende `calendarEndsAt` bajo bloqueo, no supera la proxima entrada menos limpieza y guarda observacion/cargo.
- Salida anticipada, no-show, cancelacion y reprogramacion usan conciliacion guiada.
- Reprogramar usa tarifas actuales por defecto y permite conservar originales con motivo.
- El cargo base completo se reconoce en check-in y reservas concurrentes incompatibles no se superponen.

### 18.6 Eventos

- Un evento es entidad y modalidad distinta de alojamiento.
- Inicio 15:00 y fin 03:00 del dia siguiente se guardan con fecha-hora local y UTC resuelto.
- Paquete, tipo de dia, asistentes, ajuste de precio, aforo y buffers quedan congelados al confirmar.
- Nunca se confirma por encima del aforo de la unidad.
- Todo cambio de paquete antes de check-in crea revision y conserva la anterior; despues, asistentes adicionales generan cargo separado.
- Exceder el fin crea incidencia y cargo sin desplazar la operacion posterior.
- Eventos y otros compromisos respetan matriz y bloqueo comun bajo concurrencia.

### 18.7 Pases diarios

- Una ubicacion define categorias, tarifas, franjas y cupos propios.
- Un pase guarda cantidades por categoria y responsable opcional.
- Confirmar exige pago total administrado y cupo disponible en la misma transaccion.
- Franjas semiabiertas de una ubicacion no se solapan, no cambian en sitio con pases futuros y reutilizan cupo por franja; huespedes y eventos no consumen ese cupo.
- Una venta con comprador o responsable es identificada; solo sin ambos puede ser anonima y no crear `Party`.
- Cancelar libera cupo; una venta anonima confirmada no admite reembolso.
- Cancelar un pase anonimo futuro reconoce y aplica la penalidad en `cancelledOn`, nunca en la fecha futura del pase.
- El ingreso pertenece a la organizacion y nunca entra en liquidaciones de propietarios.

### 18.8 Garantias

- La senia se clasifica como anticipo o garantia.
- Una garantia admite varias recepciones y se devuelve siempre a la parte de facturacion.
- Aplicar reduce retenido, cancela deuda y no crea otra entrada de caja.
- Revertir restaura garantia y deuda, neutraliza la fuente interna atomicamente y no mueve caja.
- Solo cubre cargos del mismo origen y puede transferirse sin caja a una renovacion con la misma parte.
- Devolver es salida no operativa y no gasto.

### 18.9 Gastos y aprobaciones

- El flujo lineal es planificado, pendiente, aprobado, incurrido y pagado.
- Un rechazo crea nueva version planificada; no se pierde la solicitud anterior.
- Cada presupuesto se aprueba por separado y cada parte propietaria emite un voto.
- Umbrales se evaluan por importe de cada imputacion.
- Cambiar partes, porcentajes, monto o alcance invalida; un exceso se bloquea salvo emergencia documentada.
- D1 muestra PYG 70.000 de plomeria y D2 desocupada PYG 500.000 incurridos con ingreso cero.
- Devolucion de proveedor y cargo trasladado al inquilino son hechos separados y no se suman dos veces.
- Existe un solo traslado por gasto; antes de emitir se revisa y despues usa ajustes.

### 18.10 Liquidaciones y periodos

- Los meses son independientes y solo se cierran despues de terminar.
- Cierre y movimiento concurrentes se serializan en la misma fila de periodo.
- Cobros sin aplicar y gastos declarados sin atribuir advierten; cuotas o cargos faltantes bloquean.
- Una liquidacion negativa es informativa, independiente y no se arrastra ni cobra.
- Una positiva admite desembolsos parciales.
- Retornos reales se enlazan al desembolso, no pueden superarlo y rehabilitan solo el importe efectivamente retornado bajo el mismo bloqueo.
- Puede revisarse sobre pagos parciales si el total no baja de lo desembolsado; si bajaria, se bloquea y ajusta en otro periodo.
- Una totalmente desembolsada no se edita y bloquea la reapertura de su periodo.
- La correccion puede ir a cualquier periodo abierto no anterior elegido, con fecha contable y motivo.
- Cobros sin aplicar solo aparecen en bandeja organizacional y fuentes compartidas no se exponen al propietario.

### 18.11 Reportes, documentos y comunicaciones

- La vista historica es predeterminada y la reformulada actual se ofrece claramente separada.
- Pantalla y PDF del mismo `ReportRun` tienen filas y totales identicos aunque entren movimientos despues.
- Alojamiento y eventos tienen indicadores de ocupacion separados y los bloqueos salen del denominador comercializable.
- Audiencia documental y periodo efectivo se congelan; solo usuarios autenticados descargan.
- La descarga usa endpoint autenticado; cualquier URL interna dura maximo cinco minutos y cada acceso sensible queda auditado.
- PDF e imagenes pasan cuarentena y antimalware.
- La politica documental conserva versiones por defecto y puede ordenar eliminacion futura conservando metadata y checksum.
- Consentimiento es por canal, un contacto nuevo lo reinicia y mensajes pendientes se cancelan si cambia.
- El bridge recibe ID opaco, destino y texto final, deduplica timeouts y conserva historial de intentos.

### 18.12 Importacion y retencion

- Una vista previa no escribe registros de dominio; solo staging temporal no respaldado, y todas las filas seleccionadas confirman o fallan juntas.
- Coincidencias de identidad son advertencias; `Location.code` duplicado es error.
- La fila crea o vincula explicitamente, nunca actualiza ni fusiona automaticamente.
- El CSV original se elimina al terminar y no se respalda.
- Un lote equivocado solo puede archivarse de forma atomica si sus registros no adquirieron dependencias.
- Historia financiera, auditoria y documentos necesarios se conservan; temporales y datos no referenciados se purgan.

## 19. Riesgos y mitigaciones

| Riesgo | Mitigacion obligatoria |
| --- | --- |
| Fuga de datos entre organizaciones | Contexto por ruta, modo explicito, sello de formulario, restricciones compuestas y pruebas cruzadas. |
| Pestana con organizacion obsoleta | Rechazar la mutacion con `CONTEXT_STALE` antes de ejecutar dominio. |
| Union indebida de equipo y portal | Modos excluyentes, permisos separados y revalidacion por solicitud. |
| Doble reserva entre modalidades | Bloqueo comun por unidad, matriz denegada por defecto y revalidacion transaccional. |
| Sobreventa de pases | Franjas no solapadas, bloqueo por ubicacion/fecha y confirmacion atomica de cupo y pago. |
| Duplicacion de cargos o mensajes | Idempotency key determinista, outbox, lease y receptor externo deduplicable. |
| Alteracion de historia financiera | Revisiones, contramovimientos tipados, fechas `On` y prohibicion de sobrescritura de confirmados. |
| Correccion en periodo equivocado | Periodo abierto elegido explicitamente, `accountingOn`, motivo y enlace al origen. |
| Hecho real omitido sin origen | Alta tardia unica con fecha real, evidencia y efecto oficial solo en `accountingOn` abierto. |
| Retorno o reembolso por encima de la fuente | Bloqueo compartido, limite neto por fuente y pruebas concurrentes. |
| Pago directo tratado como caja | Libro limitado a fondos administrados; solo una recepcion posterior real por la organizacion puede registrarse. |
| Redondeo inconsistente | Distribuciones de cuatro decimales e importes enteros materializados una sola vez. |
| Doble conteo de gastos generales | Separar alcance, imputacion y atribucion; mostrar "sin imputar". |
| Recuperacion doble de un gasto | Recuperaciones tipadas, traslado unico y referencias reciprocas. |
| Liquidacion incorrecta tras cambio de propietario | Snapshot por `recognitionOn`/`incurredOn`, revisiones y limites frente a desembolsos. |
| Neto negativo interpretado como deuda | Estado informativo, sin arrastre ni cobro automatico. |
| PDF distinto de pantalla | `ReportRun` inmutable compartido por ambas salidas. |
| Archivo malicioso | Cuarentena, allowlist, firma binaria, checksum y antimalware sin modo permisivo. |
| Borrado de version documental | Politica capturada, conservar por defecto y mantener evento/checksum cuando elimina contenido. |
| Mensaje duplicado por timeout | ID opaco estable, firma, bridge idempotente e historial de intentos. |
| Consentimiento obsoleto | Historial versionado y revalidacion antes de cada intento. |
| Suspension con backlog peligroso | Pausa por organizacion, vista previa de catch-up y omision de avisos obsoletos. |
| Worker detenido o lease abandonado | Cola persistida, heartbeat, recuperacion y handlers idempotentes. |
| Perdida de documentos | Spaces privado, checksum, respaldo de durables y restauracion probada. |
| Complejidad de alojamiento, eventos y pases | Entidades separadas, interfaces comunes minimas e incrementos 4A/4B/4C. |

## 20. Enfoques considerados

### 20.1 Monolito modular con API y worker separados

Elegido. Mantiene transacciones simples, despliegue razonable y limites de dominio claros. La API queda disponible para V2 movil y los procesos pesados no bloquean solicitudes web.

### 20.2 Monolito tradicional por capas

Descartado. Reduce estructura inicial, pero favorece el acoplamiento entre contratos, reservas, gastos, propietarios y permisos a medida que crece el producto.

### 20.3 Microservicios

Descartado para V1. Agrega mensajeria distribuida, consistencia eventual, observabilidad y despliegues complejos sin una necesidad de escala que lo justifique.

### 20.4 Decisiones de frontera cerradas

- V1 registra solo fondos administrados; el pago directo original queda fuera y una recepcion posterior real por la organizacion es un movimiento nuevo.
- Los periodos mensuales son independientes y una correccion puede publicarse en cualquier periodo abierto no anterior elegido.
- Una unidad puede tener varias modalidades vigentes y una matriz de compatibilidad propia; no existe una matriz global fija.
- Alojamiento, eventos y pases son conceptos distintos y no comparten una entidad generica de reserva.
- Contratos son finitos, materializan cuotas futuras y usan cierre de cuota ademas del cierre financiero.
- Las correcciones usan revision cuando el hecho no tiene dependencias en periodo abierto y contramovimiento en los demas casos.
- Liquidaciones negativas son informativas; liquidaciones positivas admiten desembolsos parciales y revisiones limitadas por lo ya desembolsado.
- V1 se limita a `America/Asuncion`; otras zonas se posponen.
- La retencion de versiones documentales es configurable por tipo, conserva por defecto y puede eliminar contenido reemplazado futuro conservando metadata y checksum.
- Superadministracion puede consultar siempre la auditoria ya enmascarada, pero no negocio ni archivos sin membresia.

## 21. Limites de planificacion y entregas

Este archivo es la especificacion integral de producto, no un unico ciclo de implementacion. V1 debe construirse mediante incrementos ordenados; cada incremento recibira su propio plan detallado, pruebas y puerta de aceptacion. No se debe crear un plan de implementacion monolitico para todos los modulos a la vez.

| Incremento | Alcance cerrado | Dependencia | Puerta de aceptacion |
| --- | --- | --- | --- |
| 0. Plataforma segura | Monorepo, PostgreSQL, autenticacion, organizaciones, contexto de equipo, permisos, auditoria enmascarada, API, idempotencia, outbox y worker con lease. | Ninguna. | Dos organizaciones operan sin cruce; portal deniega por defecto; stale tabs, superadmin, migraciones y cola pasan integracion. |
| 1. Cartera y modalidades | Partes, contactos versionados, ubicaciones, unidades, estados, modalidades multiples, matriz, titularidad, grants, modo portal minimo, canal CSV efimero e importacion atomica. | Incremento 0. | U1 reproduce copropiedad, portal acotado, modalidades simultaneas, combinaciones denegadas y CSV todo-o-nada. |
| 2. Contratos y finanzas | Contratos, ciclos, ocurrencias, cierre de cuotas, adendas, terminacion, cargos, mora, pagos, reversiones, garantias, apertura, alta tardia, periodos, `ReportRun` base y reportes financieros. | Incremento 1. | Fin de mes, caja administrada, pago sin aplicar, cierre concurrente, matriz correctiva, credito de apertura, alta tardia y run estable cuadran. |
| 3. Gastos y propietarios | Incidencias, gastos lineales, aprobaciones, imputaciones, devoluciones de proveedor, traslado, liquidaciones revisables, desembolsos/retornos parciales y portal financiero sin documentos/comunicaciones finales. | Incremento 2. | D1/D2, gasto general, cambio de propietario, retorno concurrente y liquidaciones positivas/negativas producen totales trazables. |
| 4. Alojamiento, eventos y pases | Calendario comun, alojamiento por noche, feriados, eventos por hora, paquetes, aforo, buffers, pases, categorias, cupos y conciliaciones. | Incrementos 1 y 2; eventos tambien depende del 3. | Carreras mixtas, evento nocturno, late checkout y ultimo cupo pasan sin sobreventa ni doble reserva. |
| 5. Documentos, comunicaciones y endurecimiento | Politicas documentales, cuarentena, antimalware, Spaces, Resend, bridge, `ReportRun`, reportes completos, observabilidad, rendimiento, accesibilidad y restauracion. | Incrementos 0 a 4. | PDF/run, timeout, consentimiento, suspension/catch-up, seguridad y restauracion pasan E2E. |

La trazabilidad minima entre requisitos e incrementos es:

- Incremento 0: `ORG`, `IAM`, base de `AUD`, contexto, API, idempotencia y worker.
- Incremento 1: `PTY`, `PRT`, `OWN`, grants, modalidades, matriz e `IMP`.
- Incremento 2: `CTR`, cuotas, adendas, `MOR`, `FIN`, `DEP`, apertura, periodos y nucleo `ReportRun`.
- Incremento 3: `EXP`, `MNT`, `LIQ`, devoluciones de proveedor y portal financiero.
- Incremento 4: `CAL`, `RSV-A`, `RSV-E`, `PAS` y sus integraciones financieras.
- Incremento 5: `DOC`, `NTF`, `ReportRun`, reportes completos y no funcionales.

El incremento 4 se divide en 4A calendario comun, 4B alojamiento, 4C eventos y 4D pases/cupos. El incremento 5 se divide en 5A documentos/archivos, 5B comunicaciones y 5C renderizado/exportacion/endurecimiento de reportes. V1 no termina hasta completar todas las puertas.

El incremento 0 implementa suspension y fencing. Cada incremento 2 a 4 agrega sus productores de catch-up; el incremento 5 completa la orquestacion operativa y la politica final de mensajes atrasados. El nucleo `ReportRun` nace en 2 y su renderizado/exportacion durable se completa en 5.

Las interfaces entre modulos se definen en el incremento que las necesita. Los incrementos posteriores no justifican crear abstracciones o tablas anticipadas fuera de las decisiones ya fijadas en esta especificacion.

## 22. Evolucion posterior

La arquitectura debe permitir incorporar sin redisenar el dominio central:

- Aplicacion movil para equipo y propietarios.
- Portales de inquilinos, huespedes, responsables de eventos y compradores de pases.
- Zonas horarias distintas de `America/Asuncion`.
- Flujo completo de compraventa.
- Facturacion electronica paraguaya.
- Pasarela, links de pago, pagos en linea y conciliacion bancaria.
- Registro de caja no administrada y pagos directos entre terceros.
- Sincronizacion con plataformas de reservas.
- Firma electronica.
- Multimoneda y cotizaciones.
- Comisiones automaticas de administradora.
- Planes, limites y cobro de suscripcion SaaS.
- Mantenimiento preventivo, proveedores y presupuestos avanzados.
- Revenue management, promociones y precios dinamicos avanzados.
- Pases recurrentes, membresias, QR y control de acceso fisico.
- Eventos con multiples recursos, planos, asientos y proveedores integrados.

Estas capacidades no forman parte de los criterios de aceptacion de V1.

Salvo la API versionada y el bridge WhatsApp exigidos por V1, esta lista no debe impulsar tablas, SDK, credenciales o abstracciones anticipadas.

## 23. Definicion de terminado para V1

V1 se considera terminada cuando:

- Todos los requisitos incluidos tienen evidencia de aceptacion.
- Las pruebas unitarias, de integracion, API, E2E y seguridad obligatorias pasan.
- Los casos `BND-01` a `BND-49` pasan y los aplicables usan PostgreSQL real y al menos dos workers.
- Aislamiento, modos, stale tabs, concurrencia, cupos e idempotencia pasan bajo carga de referencia.
- Contratos, cuotas, adendas, terminaciones y mora pasan sus fronteras de fechas y cierre.
- Alojamiento, eventos y pases pasan precio, aforo, buffer, cupo y conciliacion.
- Caja administrada, apertura, garantias, gastos y liquidaciones cuadran en historico y reformulado.
- Pantalla y PDF del mismo `ReportRun` coinciden y una mutacion posterior no los cambia.
- Consentimiento, audiencia, politicas documentales, cuarentena y antimalware pasan E2E.
- Suspension, catch-up, lease vencido y timeout del bridge no duplican efectos.
- Se cumplen los objetivos de rendimiento bajo la carga definida.
- Se completo una restauracion verificada de base, objetos durables y reportes.
- OpenAPI, variables, politicas documentales, worker, scanner, bridge y recuperacion estan documentados.
- No existen defectos conocidos que puedan perder fondos administrados, exceder cupos o aforos, duplicar compromisos, filtrar datos o alterar historia.
- No existen endpoints, SDK, secretos o callbacks de pasarelas de pago.
- Los flujos principales funcionan desde 360 px y cumplen WCAG 2.2 AA.

Este documento define el producto, sus reglas y los limites de cada entrega. La implementacion se planifica un incremento por vez, comenzando por el incremento 0.
