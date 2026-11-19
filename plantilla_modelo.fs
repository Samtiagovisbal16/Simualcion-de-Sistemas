/* =====================================================================
   CONSTRUCTOR AUTOMÁTICO DEL MODELO 
   Generado por 05_generar_flexsim.py  |  @@ESTADO@@
   ---------------------------------------------------------------------
   USO:
   1. File > New Model  ->  Time Units = MINUTES, Length Units = METERS
   2. Cambiar ESCENARIO (abajo) según el modelo que se quiere construir
   3. View > Script Console -> pegar TODO -> Execute
   4. Guardar con el nombre del escenario (ej. Esc_2_isleros_base.fsm)
   5. Para los ESCENARIOS: abrir el modelo base (que ya tiene la Performance Measure Table),
      cambiar ESCENARIO / FACTOR_DEMANDA, ejecutar este script y "Guardar como" con otro nombre.
      El script detecta el modelo existente y solo cambia isleros, código y parámetros.
   Ventana simulada: @@VENTANA@@  |  Experimenter: Run Time = @@RUNTIME@@ min, Warmup = 0
   ===================================================================== */

/* ---------------------- ESCENARIO A CONSTRUIR ------------------------
   1 = 1 solo islero para las 4 caras (reducción de personal)
   2 = BASE: 2 isleros, cada uno fijo en su isla (Islero_1: caras 1-2; Islero_2: caras 3-4)
   3 = 2 isleros fijos + Islero_3 de apoyo que ayuda a la isla que lo necesite
   4 = 4 isleros, uno fijo por cara
   FACTOR_DEMANDA: 1.0 = demanda actual; 1.5 = 50 % más vehículos; 2.0 = el doble...
   --------------------------------------------------------------------- */
int ESCENARIO = 2;
string FACTOR_DEMANDA = "1.0";
/* El cliente elige la isla según la preferencia observada; cada isla tiene su propia fila.
   UMBRAL_FILA: si una isla tiene esa cantidad de vehículos (o más) que la otra, el conductor se va a la más corta.
   "999" = nunca cambia (sigue siempre su preferencia). */
string UMBRAL_FILA = "2";

/* ---------------- PARÁMETROS (los escribe el script 05) --------------- */
@@PARAMETROS@@

/* =====================================================================
   OBJETOS
   ===================================================================== */
print("========== ESCENARIO " + string.fromNum(ESCENARIO) + " ISLEROS | DEMANDA x" + FACTOR_DEMANDA + " ==========");
/* Clases de la biblioteca 3D (rutas explícitas para no confundirlas con las de Process Flow) */
treenode L_SOURCE = library().find("fixedresources/Source");
treenode L_QUEUE  = library().find("fixedresources/Queue");
treenode L_PROC   = library().find("fixedresources/Processor");
treenode L_SINK   = library().find("fixedresources/Sink");
treenode L_OPER   = library().find("taskexecuters/Operator");
treenode L_DISP   = library().find("taskexecuters/Dispatcher");
if (!L_SOURCE) L_SOURCE = library().find("?Source");
if (!L_QUEUE)  L_QUEUE  = library().find("?Queue");
if (!L_PROC)   L_PROC   = library().find("?Processor");
if (!L_SINK)   L_SINK   = library().find("?Sink");
if (!L_OPER)   L_OPER   = library().find("?Operator");
if (!L_DISP)   L_DISP   = library().find("?Dispatcher");
print("Biblioteca: " + L_SOURCE.getPath() + " | " + L_SINK.getPath() + " | " + L_OPER.getPath());

/* Si el modelo ya existe (por ejemplo, el modelo base con su Performance Measure Table),
   NO se crea de nuevo: solo se cambian los isleros, el código y los parámetros del escenario. */
int NUEVO = (model().find("Llegadas") == 0);
Object src;  Object cola1;  Object cola2;  Object c1;  Object c2;  Object c3;  Object c4;  Object sink;
if (NUEVO) {
    src  = createinstance(L_SOURCE, model());
    cola1 = createinstance(L_QUEUE, model());
    cola2 = createinstance(L_QUEUE, model());
    c1   = createinstance(L_PROC, model());
    c2   = createinstance(L_PROC, model());
    c3   = createinstance(L_PROC, model());
    c4   = createinstance(L_PROC, model());
    sink = createinstance(L_SINK, model());
    src.name = "Llegadas";  cola1.name = "Cola_Isla1";  cola2.name = "Cola_Isla2";  sink.name = "Salida";
    c1.name = "Cara_1";  c2.name = "Cara_2";  c3.name = "Cara_3";  c4.name = "Cara_4";
    src.setLocation(-16, 0, 0);  cola1.setLocation(-8, 6, 0);  cola2.setLocation(-8, -6, 0);  sink.setLocation(12, 0, 0);
    c1.setLocation(0, 6, 0);  c2.setLocation(4, 6, 0);     // Isla 1
    c3.setLocation(0, -6, 0); c4.setLocation(4, -6, 0);    // Isla 2
    /* Flujo (A): un solo flujo de llegadas; el cliente elige la isla (puerto 1 = isla 1, puerto 2 = isla 2).
       Cada isla tiene su propia fila, que alimenta sus dos caras. */
    contextdragconnection(src, cola1, "A");
    contextdragconnection(src, cola2, "A");
    contextdragconnection(cola1, c1, "A");
    contextdragconnection(cola1, c2, "A");
    contextdragconnection(cola2, c3, "A");
    contextdragconnection(cola2, c4, "A");
    contextdragconnection(c1, sink, "A");
    contextdragconnection(c2, sink, "A");
    contextdragconnection(c3, sink, "A");
    contextdragconnection(c4, sink, "A");
    print("OK      Modelo nuevo creado");
} else {
    src = model().find("Llegadas");  cola1 = model().find("Cola_Isla1");  cola2 = model().find("Cola_Isla2");
    c1 = model().find("Cara_1");  c2 = model().find("Cara_2");  c3 = model().find("Cara_3");  c4 = model().find("Cara_4");
    sink = model().find("Salida");
    /* se retiran los isleros y despachadores del escenario anterior */
    Array viejos = ["Islero_1", "Islero_2", "Islero_3", "Islero_4", "Despacho_Isla1", "Despacho_Isla2"];
    for (int v = 1; v <= viejos.length; v++) {
        string nv = viejos[v];
        treenode ov = model().find(nv);
        if (ov) destroyobject(ov);
    }
    print("OK      Modelo existente: se conservan objetos, etiquetas y Performance Measure Table; se cambia el escenario");
}

Object op1 = createinstance(L_OPER, model());
op1.name = "Islero_1";
op1.setLocation(2, 9, 0);
Array ops = [op1];
Object op2;  Object op3;  Object op4;  Object d1;  Object d2;
if (ESCENARIO >= 2) {
    op2 = createinstance(L_OPER, model());
    op2.name = "Islero_2";
    op2.setLocation(2, -9, 0);
    ops.push(op2);
}

/* Asignación de isleros según el escenario */
if (ESCENARIO == 1) {
    op1.setLocation(2, 0, 0);
    contextdragconnection(c1, op1, "S");
    contextdragconnection(c2, op1, "S");
    contextdragconnection(c3, op1, "S");
    contextdragconnection(c4, op1, "S");
    print("OK      Islero_1 atiende las 4 caras");
}
if (ESCENARIO == 2) {
    contextdragconnection(c1, op1, "S");
    contextdragconnection(c2, op1, "S");
    contextdragconnection(c3, op2, "S");
    contextdragconnection(c4, op2, "S");
    print("OK      Isla 1 -> Islero_1 | Isla 2 -> Islero_2");
}
if (ESCENARIO == 3) {
    op3 = createinstance(L_OPER, model());
    d1 = createinstance(L_DISP, model());
    d2 = createinstance(L_DISP, model());
    op3.name = "Islero_3";  d1.name = "Despacho_Isla1";  d2.name = "Despacho_Isla2";
    op3.setLocation(2, 0, 0);  d1.setLocation(8, 9, 0);  d2.setLocation(8, -9, 0);
    contextdragconnection(c1, d1, "S");
    contextdragconnection(c2, d1, "S");
    contextdragconnection(c3, d2, "S");
    contextdragconnection(c4, d2, "S");
    contextdragconnection(d1, op1, "A");   // primero el islero de la isla
    contextdragconnection(d1, op3, "A");   // luego el de apoyo
    contextdragconnection(d2, op2, "A");
    contextdragconnection(d2, op3, "A");
    ops.push(op3);
    print("OK      Islero_3 de apoyo compartido por las dos islas (vía despachadores)");
    print("REVISAR Despacho_Isla1 y Despacho_Isla2 > Pass To = 'First Available'");
}
if (ESCENARIO == 4) {
    op3 = createinstance(L_OPER, model());
    op4 = createinstance(L_OPER, model());
    op3.name = "Islero_3";  op4.name = "Islero_4";
    op1.setLocation(0, 9, 0);  op2.setLocation(4, 9, 0);
    op3.setLocation(0, -9, 0); op4.setLocation(4, -9, 0);
    contextdragconnection(c1, op1, "S");
    contextdragconnection(c2, op2, "S");
    contextdragconnection(c3, op3, "S");
    contextdragconnection(c4, op4, "S");
    ops.push(op3);  ops.push(op4);
    print("OK      Un islero fijo por cara");
}

/* =====================================================================
   CÓDIGO
   Labels del vehículo: Type (1 moto, 2 carro, 3 camión), Producto (1 gasolina, 2 ACPM),
   tLlegada (hora de llegada), tServ (tiempo de servicio sorteado)
   ===================================================================== */
/* Todo el código va en campos confirmados en su versión de FlexSim:
   interarrivaltime (Source), sendtoport (Source, Cola, Caras) y cycletime (Caras). No se usan triggers. */

/* 1) Source > Inter-Arrivaltime: al iniciar cada réplica (tiempo 0) reinicia las etiquetas de la Salida */
string CODE_LLEGADAS =
    "Object current = ownerobject(c);\n" +
    "Object item = param(1);\n" +
    "if (Model.time == 0) {\n" +
    "  Object s = model().find(\"Salida\");\n" +
    "  s.sumWq = 0; s.nVeh = 0; s.WqProm = 0; s.VehHora = 0;\n" +
    "  s.sumWqG = 0; s.nG = 0; s.WqGasolina = 0; s.sumWqA = 0; s.nA = 0; s.WqACPM = 0;\n" +
    "  s.nC1 = 0; s.nC2 = 0; s.nC3 = 0; s.nC4 = 0; s.PC1 = 0; s.PC2 = 0; s.PC3 = 0; s.PC4 = 0;\n" +
    "  s.sumWqP = 0; s.nP = 0; s.WqPico = 0; s.VehHoraPico = 0;\n" +
    "  s.ocupIsla1 = 0; s.ocupIsla2 = 0; s.UtilIsla1 = 0; s.UtilIsla2 = 0;\n" +
    "  treenode tn = model().find(\"Tools/GlobalTables/TablaWq\");\n" +
    "  if (tn) Table(\"TablaWq\").setSize(0, 4);\n" +
    "}\n" + PRE_LLEGADAS +
    "return (" + EXP_LLEGADAS + ") / " + FACTOR_DEMANDA + ";\n";

/* 2) Source > Send To Port: se ejecuta al crear cada vehículo -> tipo, producto y hora de llegada */
string CODE_CREACION =
    "Object current = ownerobject(c);\n" +
    "Object item = param(1);\n" +
    "int r = duniform(1, 100, getstream(current));\n" +
    "int tipo = 3;\n" +
    "if (r <= " + LIM_MOTO + ") tipo = 1;\n" +
    "else if (r <= " + LIM_CARRO + ") tipo = 2;\n" +
    "item.labels.assert(\"Tipo\").value = tipo;\n" +
    "double pA = (tipo == 1) ? " + P_ACPM_MOTO + " : ((tipo == 2) ? " + P_ACPM_CARRO + " : " + P_ACPM_CAMION + ");\n" +
    "item.labels.assert(\"Producto\").value = bernoulli(pA, 2, 1, getstream(current));\n" +
    "item.color = Color.byNumber(tipo);\n" +
    "item.labels.assert(\"tLlegada\").value = Model.time;\n" +
    "item.labels.assert(\"tServ\").value = 0;\n" +
    "item.labels.assert(\"tProc\").value = 0;\n" +
    "item.labels.assert(\"tPrep\").value = 0;\n" +
    "item.labels.assert(\"Cara\").value = 0;\n" +
    "Array w = (tipo == 1) ? " + W_MOTO + " : ((tipo == 2) ? " + W_CARRO + " : " + W_CAMION + ");\n" +
    "double p1 = w[1] + w[2];\n" +
    "int isla = (uniform(0, p1 + w[3] + w[4], getstream(current)) < p1) ? 1 : 2;\n" +
    "/* Si una isla tiene UMBRAL_FILA o más vehículos que la otra, el conductor se va a la más corta */\n" +
    "int n1 = model().find(\"Cola_Isla1\").subnodes.length + model().find(\"Cara_1\").subnodes.length + model().find(\"Cara_2\").subnodes.length;\n" +
    "int n2 = model().find(\"Cola_Isla2\").subnodes.length + model().find(\"Cara_3\").subnodes.length + model().find(\"Cara_4\").subnodes.length;\n" +
    "if (n1 - n2 >= " + UMBRAL_FILA + ") isla = 2;\n" +
    "if (n2 - n1 >= " + UMBRAL_FILA + ") isla = 1;\n" +
    "item.labels.assert(\"Isla\").value = isla;\n" +
    "return isla;\n";

/* 3) Cara > Process Time: guarda la cara y sortea el servicio según tipo y producto */
string CODE_SERVICIO = PRE_SERVICIO +
    "double t;\n" +
    "if (item.Tipo == 1) t = (item.Producto == 2) ? " + EXP_MOTO_A + " : " + EXP_MOTO_G + ";\n" +
    "else if (item.Tipo == 2) t = (item.Producto == 2) ? " + EXP_CARRO_A + " : " + EXP_CARRO_G + ";\n" +
    "else t = (item.Producto == 2) ? " + EXP_CAMION_A + " : " + EXP_CAMION_G + ";\n" +
    "item.tServ = t;\n" +
    "return t;\n";
Array CODE_CARA = [];
for (int k = 1; k <= 4; k++) {
    CODE_CARA.push("Object current = ownerobject(c);\n" +
                   "Object item = param(1);\n" +
                   "item.Cara = " + string.fromNum(k) + ";\n" + CODE_SERVICIO);
}

/* 3b) MULTITAREA: el islero atiende en el Setup (con operario) y el surtidor despacha en el Process (sin operario).
   Moto: todo el servicio con el islero (Setup) y Process = 0.
   Carro y camión: el islero solo hace el cobro (Setup) y queda libre mientras el surtidor marca (Process = flujo).
   Simplificación: el cobro se ubica antes del flujo; el tiempo total del islero y de la cara se conserva. */
Array CODE_SETUP = [];
for (int k = 1; k <= 4; k++) {
    CODE_SETUP.push("Object current = ownerobject(c);\n" +
        "Object item = param(1);\n" +
        "item.Cara = " + string.fromNum(k) + ";\n" + PRE_SERVICIO +
        "double islero = 0;  double flujo = 0;\n" +
        "double prep = " + EXP_PREP + ";\n" +
        "if (item.Tipo == 1) { islero = " + EXP_MOTO_G + "; flujo = 0; }\n" +
        "else if (item.Tipo == 2) { flujo = (item.Producto == 2) ? " + EXP_CARRO_A + " : " + EXP_CARRO_G + "; islero = " + EXP_COBRO + "; }\n" +
        "else { flujo = (item.Producto == 2) ? " + EXP_CAMION_A + " : " + EXP_CAMION_G + "; islero = " + EXP_COBRO + "; }\n" +
        "islero += prep;\n" +
        "item.tPrep = prep;\n" +
        "item.tProc = flujo;\n" +
        "item.tServ = islero + flujo;\n" +
        "return islero;\n");
}
string CODE_PROC =
    "Object current = ownerobject(c);\n" +
    "Object item = param(1);\n" +
    "return item.tProc;\n";

/* 4) Cara > Send To Port: al TERMINAR el despacho calcula Wq = ahora - llegada - servicio */
string CODE_FIN =
    "Object current = ownerobject(c);\n" +
    "Object item = param(1);\n" +
    "if (item.tLlegada >= " + WARMUP + ") {\n" +
    "  Object s = model().find(\"Salida\");\n" +
    "  double wq = Model.time - item.tLlegada - item.tServ;\n" +
    "  if (wq < 0) wq = 0;\n" +
    "  s.sumWq += wq;  s.nVeh += 1;\n" +
    "  s.WqProm = s.sumWq / s.nVeh;\n" +
    "  s.VehHora = s.nVeh / (" + DURACION + " / 60.0);\n" +
    "  if (item.Cara == 1) s.nC1 += 1; else if (item.Cara == 2) s.nC2 += 1;\n" +
    "  else if (item.Cara == 3) s.nC3 += 1; else s.nC4 += 1;\n" +
    "  s.PC1 = 100 * s.nC1 / s.nVeh;  s.PC2 = 100 * s.nC2 / s.nVeh;\n" +
    "  s.PC3 = 100 * s.nC3 / s.nVeh;  s.PC4 = 100 * s.nC4 / s.nVeh;\n" +
    "  if (item.Producto == 2) { s.sumWqA += wq; s.nA += 1; s.WqACPM = s.sumWqA / s.nA; }\n" +
    "  else { s.sumWqG += wq; s.nG += 1; s.WqGasolina = s.sumWqG / s.nG; }\n" +
    "  /* carga de trabajo del islero de cada isla (sin el flujo, en que el islero queda libre) */\n" +
    "  double ocup = item.tServ - item.tProc;\n" +
    "  if (item.Cara <= 2) s.ocupIsla1 += ocup; else s.ocupIsla2 += ocup;\n" +
    "  s.UtilIsla1 = 100 * s.ocupIsla1 / " + DURACION + ";  s.UtilIsla2 = 100 * s.ocupIsla2 / " + DURACION + ";\n" +
    "  if (item.tLlegada >= " + PICO_INI + " && item.tLlegada < " + PICO_FIN + ") {\n" +
    "    s.sumWqP += wq + item.tPrep; s.nP += 1; s.WqPico = s.sumWqP / s.nP;\n" +
    "    s.VehHoraPico = s.nP / ((" + PICO_FIN + " - " + PICO_INI + ") / 60.0);\n" +
    "  }\n" +
    "  treenode tn = model().find(\"Tools/GlobalTables/TablaWq\");\n" +
    "  if (tn) {\n" +
    "    Table tb = Table(\"TablaWq\");\n" +
    "    tb.addRow();  int f = tb.numRows;\n" +
    "    tb[f][1] = item.Tipo;  tb[f][2] = item.Producto;  tb[f][3] = item.tLlegada;  tb[f][4] = wq;\n" +
    "  }\n" +
    "}\n" +
    "return 1;\n";

/* 5) Cola de cada isla > Send To Port:
      - Motos: van al lado donde suele atender el islero (preferencia observada) y esperan ahí.
      - Carros y camiones: toman la cara libre de la isla (con preferencia si ambas están libres). */
Array CODE_RUTEO = [];
for (int k = 0; k <= 1; k++) {
    string a = string.fromNum(2 * k + 1);  string b = string.fromNum(2 * k + 2);
    CODE_RUTEO.push("Object current = ownerobject(c);\n" +
        "Object item = param(1);\n" +
        "Array w = (item.Tipo == 1) ? " + W_MOTO + " : ((item.Tipo == 2) ? " + W_CARRO + " : " + W_CAMION + ");\n" +
        "double wa = w[" + a + "];  double wb = w[" + b + "];\n" +
        "/* Motos: se forman detrás de la cara donde suele estar el islero (preferencia observada),\n" +
        "   aunque la otra cara esté libre, porque ven al islero atendiendo de ese lado */\n" +
        "if (item.Tipo == 1) return (uniform(0, wa + wb, getstream(current)) < wa) ? 1 : 2;\n" +
        "int la = (current.outObjects[1].subnodes.length == 0);\n" +
        "int lb = (current.outObjects[2].subnodes.length == 0);\n" +
        "if (la && lb) return (uniform(0, wa + wb, getstream(current)) < wa) ? 1 : 2;\n" +
        "if (la) return 1;\n" +
        "if (lb) return 2;\n" +
        "return 0;\n");
}

Array objs   = [src, src, c1, c2, c3, c4, c1, c2, c3, c4];
Array campos = ["interarrivaltime", "sendtoport", "cycletime", "cycletime", "cycletime", "cycletime",
                "sendtoport", "sendtoport", "sendtoport", "sendtoport"];
Array codes  = [CODE_LLEGADAS, CODE_CREACION, CODE_CARA[1], CODE_CARA[2], CODE_CARA[3], CODE_CARA[4],
                CODE_FIN, CODE_FIN, CODE_FIN, CODE_FIN];
Array desc   = ["Llegadas > Inter-Arrivaltime", "Llegadas > Send To Port (tipo, producto, hora)",
                "Cara_1 > Process Time", "Cara_2 > Process Time", "Cara_3 > Process Time", "Cara_4 > Process Time",
                "Cara_1 > Send To Port (cálculo de Wq)", "Cara_2 > Send To Port (cálculo de Wq)",
                "Cara_3 > Send To Port (cálculo de Wq)", "Cara_4 > Send To Port (cálculo de Wq)"];
if (MULTITAREA == 1) {
    /* Process Time = flujo (sin islero) y Setup Time = atención del islero */
    for (int k = 1; k <= 4; k++) { codes[2 + k] = CODE_PROC; }
    Array cs = [c1, c2, c3, c4];
    for (int k = 1; k <= 4; k++) {
        objs.push(cs[k]);  campos.push("setuptime");  codes.push(CODE_SETUP[k]);
        desc.push("Cara_" + string.fromNum(k) + " > Setup Time (atención del islero)");
    }
}
objs.push(cola1);  campos.push("sendtoport");  codes.push(CODE_RUTEO[1]);  desc.push("Cola_Isla1 > Send To Port (cara 1 o 2)");
objs.push(cola2);  campos.push("sendtoport");  codes.push(CODE_RUTEO[2]);  desc.push("Cola_Isla2 > Send To Port (cara 3 o 4)");
for (int i = 1; i <= objs.length; i++) {
    Object o = objs[i];
    string campo = campos[i];
    string texto = codes[i];
    string d = desc[i];
    treenode n = o.find(">variables/" + campo);    // SOLO el nombre exacto: nunca se adivina
    if (n) {
        n.value = texto;
        switch_flexscript(n, 1);
        buildnodeflexscript(n);
        print("OK      " + d);
    } else {
        print("MANUAL  " + d + "  (no existe '" + campo + "'). Código para pegar:");
        print(texto);
    }
}

/* =====================================================================
   PROPIEDADES Y ETIQUETAS
   ===================================================================== */
Array colas = [cola1, cola2];
for (int q = 1; q <= 2; q++) {
    Object cq = colas[q];
    treenode mc = cq.find(">variables/maxcontent");
    if (mc) { mc.value = 1000; print("OK      " + cq.name + " > Maximum Content = 1000"); }
    else print("MANUAL  " + cq.name + " > Maximum Content = 1000");
}

for (int i = 1; i <= ops.length; i++) {
    Object op = ops[i];
    treenode ms = op.find(">variables/maxspeed");
    if (ms) { ms.value = VEL_ISLERO; print("OK      " + op.name + " > Max Speed = 60 m/min"); }
    else print("MANUAL  " + op.name + " > Max Speed = 60 (m/min)");
}

Array etiquetas = ["sumWq", "nVeh", "WqProm", "VehHora", "sumWqG", "nG", "WqGasolina", "sumWqA", "nA", "WqACPM",
                    "nC1", "nC2", "nC3", "nC4", "PC1", "PC2", "PC3", "PC4", "sumWqP", "nP", "WqPico", "VehHoraPico",
                    "ocupIsla1", "ocupIsla2", "UtilIsla1", "UtilIsla2"];
if (1) {
    for (int i = 1; i <= etiquetas.length; i++) {
        string et = etiquetas[i];
        sink.labels.assert(et).value = 0;
    }
    print("OK      Salida > Labels WqProm, VehHora, WqGasolina, WqACPM, PC1..PC4 (% por cara)");
} else {
    print("MANUAL  Salida > pestaña Labels: crear (Number = 0): sumWq, nVeh, WqProm, VehHora, sumWqG, nG, WqGasolina,");
    print("        sumWqA, nA, WqACPM, nC1, nC2, nC3, nC4, PC1, PC2, PC3, PC4");
}

/* "Use Operator(s) for Process" en las 4 caras (nombres internos confirmados en su versión de FlexSim) */
Array caras = [c1, c2, c3, c4];
int marcadas = 0;
for (int k = 1; k <= 4; k++) {
    Object cara = caras[k];
    treenode u  = cara.find(">variables/useprocessoperators");
    treenode nr = cara.find(">variables/nrofprocessoperators");
    treenode pe = cara.find(">variables/preemptprocessoperators");
    if (u && nr) { u.value = 1; nr.value = 1; marcadas++; }
    if (MULTITAREA == 1) {
        treenode us = cara.find(">variables/usesetupoperators");
        treenode ns = cara.find(">variables/nrofsetupoperators");
        treenode so = cara.find(">variables/usesameop");
        if (us && ns) { us.value = 1; ns.value = 1; }
        if (u) u.value = 0;           // durante el flujo el surtidor trabaja solo
        if (so) so.value = 0;
    }
    if (pe) pe.value = 0;   // nunca interrumpir un despacho en curso
    treenode tr = cara.find(">variables/usetransport");
    if (tr) tr.value = 0;   // la conexión S activa "Use Transport": el islero NO lleva el carro a la salida
}
if (marcadas == 4 && MULTITAREA == 1) print("OK      Cara_1..4 > MULTITAREA: islero en Setup (sí), Process sin islero, sin interrupción, Use Transport = NO");
else if (marcadas == 4) print("OK      Cara_1..4 > Use Operator(s) for Process = sí, 1 operario, sin interrupción, Use Transport = NO");
else print("MANUAL  Cara_1..Cara_4 > Processor: marcar 'Use Operator(s) for Process', Number of Operators = 1");

print("");
print("========== PASOS MANUALES ==========");
print("1. Abrir cada cara y confirmar 'Use Operator(s) for Process' marcado, Number of Operators = 1.");
print("2. (Opcional) Toolbox > Global Table 'TablaWq': 0 filas x 4 columnas (Tipo, Producto, tLlegada, Wq_min).");
print("3. Reset + Run con animación y revisar la lista de verificación de la guía.");
print("4. Experimenter: Run Time = @@RUNTIME@@ min, Warmup = 0. Medidas: WqProm, VehHora, PC1..PC4, WqPico, VehHoraPico, WqGasolina, WqACPM y utilización de cada islero.");
print("Si algo dice MANUAL o sale un error en rojo, copiar el mensaje y enviarlo.");
print("========== FIN ==========");