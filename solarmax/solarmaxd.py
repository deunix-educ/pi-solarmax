#!../.venv/bin/python
##!/opt/lib/python/venv_app/bin/python
'''
Created on 7 nov. 2023

@author: denis
'''
import threading, logging, argparse
from SolarMax.solarmax_fr import SolarMax, get_status_code
from contrib.mqttc import MqttBase
from contrib import utils


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


INVERTERS = {
    '192.168.1.123': [1,],
    #'192.168.0.202': [2,],
    #'192.168.0.203': [3,],
    #'192.168.0.204': [4,],
}

ACCESS = [
    (1, "Pub only"),
    (2, "/set only"),
    (5, "/get, pub"),
    (7, "/get, /set, pub"),
]

class SolarmaxMqttWorker(MqttBase):

    def __init__(self, parent=None, **p):
        super().__init__(**p)
        self.parent = parent

    def makeReport(self):
        data = dict(
            name = 'Onduleur Solarmax',
            uuid = self.parent.uuid,
            sensor = 'solarmax',
            vendor = 'Solarmax',
            model_id = 'SM2000S',
            description = "Onduleur Solarmax SM2000S, 1980 W",
            ip = self.parent.ip,
            org = self.parent.org,
            datas = [
                {"access":1,"description":"Linux timestamp en secondes","label":"Timestamp","name":"time","property":"time","type":"numeric","unit":"s"},
                {"access":1,"description":"Numéro d'onduleur","label":"Inverter","name":"inv","property":"range","type":"numeric","unit":""},
                {"access":1,"description":"Intensité max","label":"Ivmax","name":"ivmax","property":"intensity","type":"numeric","unit":"A"},
                {"access":1,"description":"Production AC","label":"PAC","name":"pac","property":"power","type":"numeric","unit":"W"},
                {"access":1,"description":"Rendement AC","label":"Eac","name":"eac","property":"efficiency","type":"numeric","unit":""},
                {"access":1,"description":"Production DC.","label":"PDC","name":"pdc","property":"power","type":"numeric","unit":"W"},
                {"access":1,"description":"Efficacity DC","label":"Edc","name":"edc","property":"efficiency","type":"numeric","unit":""},
                {"access":1,"description":"Production du jour","label":"Qday","name":"qdy","property":"days","type":"numeric","unit":"kWh"},
                {"access":1,"description":"Production totale","label":"Qtotal","name":"qt0","property":"days","type":"numeric","unit":"kWh"},
                {"access":1,"description":"Status onduleur","label":"Status","name":"stat","property":"state","type":"text","unit":""},
                {"access":1,"description":"Température des panneaux","label":"Temperature","name":"tmpr","property":"temperature","type":"numeric","unit":"°C"},
            ],
        )
        return data


    def publish_to_client(self, evt, **payload):
        #logger.info(f"{self.topic_base}/{utils.ts_now()}/{evt}\n{payload}")
        self._publish_message(f'{self.topic_base}/{evt}', **payload)


    def _on_stop_mqtt(self):
        self.publish_to_client('stop', alive=False)
        logger.info(f'WAITING 1s for last message')
        threading.Event().wait(1)


    def _on_connect_info(self, info):
        logger.info(f"{info}\n    subs: {self.subscriptions}")
        self.publish_to_client('report', retain=True, **self.makeReport())


    def _on_message_callback(self, topic, payload):
        try:
            pass
            #if topic.endswith('registry'):
            #    self.publish_to_client('report', **self.makeReport())

        except Exception as e:
            logger.error(e)


class SolarmaxDaemon():

    def __init__(self, conf_file, **settings):
        super().__init__()
        self.conf_file = conf_file
        self.settings = settings
        topic_subs = self.settings['solarmax']['topic_subs']
        topic_base = self.settings['solarmax']['topic_base']
        inverters = self.settings['solarmax']['inverters']
        self.timeout = self.settings['solarmax']['loop_timeout']
        self.uuid = hex(self.settings['solarmax']['uuid'])
        self.ip =  self.settings['solarmax']['ip']
        self.org =  self.settings['solarmax']['origine']
        self.solar_stop = threading.Event()

        self.smlist = []
        for host in inverters.keys():
            sm = SolarMax(host, 12345)
            sm.use_inverters(inverters[host])
            self.smlist.append(sm)

        self.allinverters = []
        for host in inverters.keys():
            self.allinverters.extend(inverters[host])

        self.inverters_size = len(self.allinverters)
        self.mqtt = SolarmaxMqttWorker(parent=self, topic_base=topic_base ,topic_subs=topic_subs, **settings['mqtt'])
        self.mqtt.connectMQTT()


    def start(self):
        self.mqtt.client.loop_start()
        self.run_forever()


    def stop(self):
        self.mqtt.client.loop_stop()
        self.solar_stop.set()


    def run_forever(self):
        logger.info(f'Module SolarmaxDaemon::run_forever is started')
        while not self.solar_stop.is_set():
            try:
                count = 0
                for sm in self.smlist:
                    for (no, ivdata) in sm.inverters().items():
                        try:
                            (inverter, current) = sm.query(no, ['PAC', 'TKK', 'KDY', 'KT0', 'IDC', 'UDC', 'IL1', 'UL1', 'FDAT', 'SYS'])
                            count += 1
                        except:
                            logger.info(f'Erreur de communication, éventuellement onduleur éteint, WR {no}')
                            threading.Event().wait(self.timeout)
                            continue
                        ivmax = ivdata['installed']
                        ivname = ivdata['desc']
                        UAC = current['UL1']
                        IAC = current['IL1']
                        PAC = UAC * IAC
                        IDC = current['IDC']
                        UDC = current['UDC']
                        tmpr = current['TKK']
                        eac = int((PAC/ivmax) * 100)        # rendement AC
                        PDC = UDC * IDC
                        edc = int((float(PAC)/PDC) * 100)   # efficacity DC

                        (status, errors) = sm.status(no)
                        if errors:
                            logger.error(f'WR {no}: {status} ({errors})')
                            continue

                        logger.debug(
f'''
    Onduleur..............: n° {inverter} ({ivname})
    Status................: {status}
    Température panneaux..: {tmpr} °C
    Tension CC............: {UDC} V
    Intensité CC..........: {IDC} A
    Tension AC............: {UAC} V
    Intensité AC..........: {IAC} A
    Production AC.........: {current['PAC']:9.1f} Watt / calculée: {PAC:9.1f} W  rendement: ({eac}% de {ivmax} Watt)
    Production DC.........: {PDC:9.1f} Watt (Efficacité: {edc}%)
    Total aujourd'hui.....: {current['KDY']:9.1f} kWh
    Total jusqu'à présent.: {current['KT0']:9.1f} kWh (depuis le {current['FDAT'].date()})
'''
                        )
                if count < self.inverters_size:
                    raise Exception(f"({count} < {self.inverters_size} => Erreur de communication, éventuellement onduleur éteint")

                payload = dict(
                    time=utils.ts_now(),
                    inv=inverter,
                    ivmax=ivmax,
                    tmpr=tmpr,
                    pac=round(PAC, 1),
                    eac=eac,
                    pdc=round(PDC, 1),
                    edc=edc,
                    qdy=current['KDY'],
                    qt0=current['KT0'],
                    stat=get_status_code(status),
                )
                self.mqtt.publish_to_client('production', **payload)
            except Exception as e:
                logger.error(e)
            threading.Event().wait(self.timeout)


def load_configuration(conf_file):
    settings = utils.yaml_load(conf_file)
    if not settings['solarmax']['uuid']:
        uuid = f'0x{utils.gen_device_uuid(19)}'
        origine = settings['solarmax']['origine']
        settings['solarmax']['uuid'] = uuid
        settings['solarmax']['inverters'] = INVERTERS
        settings['solarmax']['topic_base'] = f"{origine}/{uuid}"
        settings['solarmax']['topic_subs']= [[f"{origine}/{uuid}/#", 0], ]
        utils.yaml_save(conf_file, settings)
    return settings


def main(conf_file):
    daemon = None
    try:
        config = load_configuration(conf_file)
        daemon = SolarmaxDaemon(conf_file, **config)
        daemon.start()

    except Exception as e:
        print(f'\n    SolarmaxDaemon error {e}')
    finally:
        if daemon:
            daemon.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Solarmax device")
    parser.add_argument("--config", default='config.yaml', help="Config yaml file path", required=False)
    args = parser.parse_args()
    if args.config:
        main(args.config)


