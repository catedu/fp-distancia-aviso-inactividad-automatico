#!/bin/bash
set -eu
# Initial Deploy
# Ver. 0.1 - bash
#
# Two options
# 1- one instance: createMoodle.sh -e mail -l language -n "full_name" -u "url" )
# 2- -f file: CSV - several instances

# Load env variables:
set -a
[ -f .env ] && . .env
set +a

usage () {
    echo 'usage: main.sh [-d dias]'
    echo "help: createMoodle.sh -h"
}

showHelp () {
    echo 'usage: main.sh [-d dias]'
    echo "Options:"
    echo "-d -> dias de inactividad a partir de los cuales se avisa"
    echo "-h this message"
}

get_parameter(){
    while getopts ":d:h" opt; do
        case $opt in
            d)
                [[ "${OPTARG}" =~ ^[0-9]+$ ]] || \
                { echo "Los días deben ser un número..."; usage; exit 1;}
                DIAS="${OPTARG}"
            ;;
            h)
                showHelp
                exit 0
            ;;
            \?)
                echo "Invalid option: -${OPTARG}" >&2
                exit 1
            ;;
            :)
                echo "Option -${OPTARG} requiere a field" >&2
                exit 1
            ;;
        esac
    done
}

DIAS=10

get_parameter "$@"

echo "dias: ${DIAS}"


# Consulta a la base de datos de Moodle para obtener los usuarios inactivos
usuarios_inactivos=$(mysql -u usuario -pcontraseña -D moodle -e "SELECT usuario FROM usuarios WHERE ultima_conexion < DATE_SUB(NOW(), INTERVAL 10 DAY)")

# Recorre la lista de usuarios inactivos y envía un email a cada uno
while IFS= read -r usuario; do
    asunto="Aviso"
    cuerpo="Su última conexión al curso fue el día $(mysql -u usuario -pcontraseña -D moodle -e "SELECT fecha_ultima_conexion FROM usuarios WHERE usuario='$usuario'")"
    echo "$cuerpo" | mail -s "$asunto" "$usuario@example.com"
done <<< "$usuarios_inactivos"
