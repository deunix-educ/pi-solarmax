# pi-solarmax
Solarmax mqtt device for django-automation


#### Installation
Cloner ou télécharger le code depuis https://github.com/deunix-educ/pi-solarmax

        git clone git@github.com:deunix-educ/pi-solarmax.git
        ou
        tar xzfv pi-solarmax-main.zip
        mv pi-solarmax-main pi-solarmax
        
        cd pi-solarmax

- Dans répertoire etc on trouve:

    - bin: quelques utilitaires
    - conf: exemple de configuration pour un pi
    - install: exemple d'installation système pour un pi
    
- Installer les packages suivants:

        sudo apt update
        sudo apt -y install build-essential git supervisor
        sudo apt -y python3-dev python3-pip python3-venv
        sudo cp /etc/supervisor/supervisord.conf /etc/supervisor/supervisord.conf.old
        sudo cat >> /etc/supervisor/supervisord.conf << EOF
        [inet_http_server]
        port=*:9001
        username=root
        password=toor
        EOF

- Changer les droits des fichiers suivants

        chmod +x solarmax/*.py
        chmod +x etc/bin/*.sh

- Installer l'environnement virtuel python (dans .venv)

        etc/bin/venv-install etc/install/requirements.txt

- Enfin installer le fichier de configuration service supervisor

        sudo cp etc/conf/solarmax_service.conf /etc/supervisor/conf.d/
        sudo supervisorctl reread && sudo supervisorctl update

#### Fonctionnement 

        cd solarmax

- Modifier et copier config_example.yaml

        cp config_example.yaml config.yaml
        ./solarmaxd.py