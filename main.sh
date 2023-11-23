#!/bin/bash

# Consulta a la base de datos de Moodle para obtener los usuarios inactivos
usuarios_inactivos=$(mysql -u usuario -pcontraseña -D moodle -e "SELECT usuario FROM usuarios WHERE ultima_conexion < DATE_SUB(NOW(), INTERVAL 10 DAY)")

# Recorre la lista de usuarios inactivos y envía un email a cada uno
while IFS= read -r usuario; do
    asunto="Aviso"
    cuerpo="Su última conexión al curso fue el día $(mysql -u usuario -pcontraseña -D moodle -e "SELECT fecha_ultima_conexion FROM usuarios WHERE usuario='$usuario'")"
    echo "$cuerpo" | mail -s "$asunto" "$usuario@example.com"
done <<< "$usuarios_inactivos"
