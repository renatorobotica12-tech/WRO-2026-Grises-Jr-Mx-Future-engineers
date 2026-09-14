"""Giroscopio: AbsoluteIMU leido desde ev3dev.

Cubre lo que en el programa de Arath hace la extension MPU6050
(`prepararFacil`, `iniciar`, `calibrar`, `actualizar`, `zonaMuerta`,
`angulo(Z)`, `reiniciarAngulos`) y lo que en EV3-G hacen los bloques
`IMU_Calibrar_WRO` e `IMU_Giro_WRO`.

El sensor entrega velocidad angular. El angulo se obtiene integrando esa
velocidad contra el tiempo real transcurrido, igual que el bloque
IMU_ANGULO documentado en documentos/BLOQUE_GIRO_ABSOLUTEIMU_EV3.md.
"""

import time

from . import config, i2c, ports

# Mapa de registros del mindsensors AbsoluteIMU-ACG.
# Confirmelo contra la hoja de datos antes de confiar en el backend 'raw'.
REG_COMANDO = 0x41
REG_GIRO_X = 0x53                   # 6 bytes: X, Y, Z en 16 bits little endian


class _LectorDriver(object):
    """Usa el driver ms-absolute-imu de ev3dev.

    En este robot ev3dev detecta el AbsoluteIMU solo, con el puerto en
    modo `auto`, y lo expone como `ev3-ports:in2:i2c17` (17 = 0x11). Por
    eso primero se intenta usarlo tal cual: forzar el modo del puerto
    cuando ya funciona lo desconectaria y habria que reiniciar.

    El camino manual queda como respaldo por si algun dia no lo detecta.
    """

    def __init__(self):
        from ev3dev2.sensor import Sensor

        try:
            self.sensor = Sensor(config.PUERTO_IMU)
            if self.sensor.driver_name != config.IMU_DRIVER:
                raise ValueError('driver inesperado: %s'
                                 % self.sensor.driver_name)
        except Exception:
            ports.poner_nxt_i2c(config.PUERTO_IMU, config.IMU_DRIVER,
                                config.IMU_DIRECCION)
            self.sensor = Sensor(config.PUERTO_IMU)

        # Arranca en COMPASS; hay que pasarlo a GYRO explicitamente.
        self.sensor.mode = config.IMU_MODO

    def crudo(self):
        return self.sensor.value(config.IMU_EJE)

    def crudo_todos(self):
        """Los tres ejes. Lo usa el diagnostico para averiguar cual es el
        eje vertical de este montaje."""
        return [self.sensor.value(i) for i in range(3)]


class _LectorRaw(object):
    """Lee los registros del giroscopio por I2C directo."""

    def __init__(self):
        ports.poner_other_i2c(config.PUERTO_IMU)
        self.bus = i2c.abrir(config.PUERTO_IMU)
        self.direccion = config.IMU_DIRECCION

    def crudo(self):
        return self.crudo_todos()[config.IMU_EJE]

    def crudo_todos(self):
        datos = i2c.leer_registros(self.bus, self.direccion, REG_GIRO_X, 6)
        ejes = []
        for eje in range(3):
            valor = datos[eje * 2] | (datos[eje * 2 + 1] << 8)
            if valor >= 0x8000:
                valor -= 0x10000
            ejes.append(valor)
        return ejes


class Giroscopio(object):
    """Velocidad angular calibrada y angulo acumulado del eje elegido."""

    def __init__(self, backend=None, escala=None):
        backend = backend or config.IMU_BACKEND
        self.escala = config.IMU_ESCALA if escala is None else escala
        self.lector = _LectorDriver() if backend == 'driver' else _LectorRaw()

        self.offset = 0.0
        self.grados = 0.0
        self.velocidad = 0.0
        self._ultimo = time.time()

        # Conteo de esquinas. Ver es_esquina().
        self.esquinas_descartadas = 0
        self._ultima_esquina = 0.0

    # ----------------------------------------------------------------

    def calibrar(self, muestras=None, mostrar=None):
        """Promedia el cero con el robot inmovil.

        Equivale a mpu.calibrar(600) de Arath y a IMU_Calibrar_WRO en EV3-G.
        Si el robot se mueve durante esta llamada, el conteo de esquinas
        de toda la carrera queda mal.
        """
        muestras = muestras or config.IMU_MUESTRAS_CALIBRACION
        suma = 0.0
        for i in range(muestras):
            suma += self.lector.crudo()
            if mostrar and i % 50 == 0:
                mostrar(i, muestras)
            time.sleep(0.002)
        self.offset = suma / muestras
        self.reiniciar()
        return self.offset

    def reiniciar(self):
        """Pone el angulo acumulado en cero. Equivale a reiniciarAngulos()."""
        self.grados = 0.0
        self._ultimo = time.time()

    def actualizar(self):
        """Lee el sensor e integra. Llamar una sola vez por vuelta de lazo."""
        ahora = time.time()
        dt = ahora - self._ultimo
        self._ultimo = ahora

        velocidad = (self.lector.crudo() - self.offset) * self.escala

        # Zona muerta: por debajo de este ruido se considera quieto, para
        # que el angulo no derive mientras el robot va recto.
        if abs(velocidad) < config.IMU_ZONA_MUERTA:
            velocidad = 0.0

        self.velocidad = velocidad
        self.grados += velocidad * dt
        return self.grados

    def es_esquina(self):
        """True cuando el giro acumulado pasa el umbral de esquina.

        Reune en un solo sitio lo que antes estaba copiado en open_ard.py
        y obs_ard.py: comparar contra ANGULO_ESQUINA y reiniciar el
        angulo. Va aqui para que no puedan volver a divergir.

        Ademas descarta las esquinas falsas. El giroscopio no distingue el
        giro de una esquina de pista del de un esquive de bloque: cuando
        la camara manda el volante al tope, el robot gira de verdad y
        acumula los 87 grados igual. Medido en pista: dos esquinas
        separadas por 1.1 s, cuando las reales iban cada 6.

        Por eso una esquina que llega antes de ESQUINA_INTERVALO_MINIMO se
        da por falsa. El angulo se reinicia igualmente, porque ese giro ya
        se hizo y arrastrarlo sumaria a la siguiente.

        Llamar una sola vez por vuelta de lazo, despues de actualizar().
        """
        if abs(self.grados) < config.ANGULO_ESQUINA:
            return False

        ahora = time.time()
        if ahora - self._ultima_esquina < config.ESQUINA_INTERVALO_MINIMO:
            self.esquinas_descartadas += 1
            self.reiniciar()
            return False

        self._ultima_esquina = ahora
        self.reiniciar()
        return True

    @property
    def vueltas(self):
        return self.grados / 360.0
