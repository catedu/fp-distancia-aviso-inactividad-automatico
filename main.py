import mysql.connector
import smtplib
import os
import sys
import io
import smtplib
import ssl
import traceback
from datetime import datetime, timedelta
from datetime import datetime
from Config import *
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


###################################################
###################################################
###################################################
# Funciones (excepto main):
###################################################
###################################################
###################################################
def abrir_conexion():

    conexion = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=3306,
    )

    return conexion

def send_email(destinatario, asunto, texto):
    print("send_email(destinatario: '" + destinatario + "')")
    """
    Al destinatario envía un email con el asunto y texto dados
    """
    enviado = False
    port = SMTP_PORT  # For starttls
    smtp_server = SMTP_HOSTS
    sender_email = SMTP_USER
    receiver_email = destinatario
    password = SMTP_PASSWORD
    texto = texto.encode('utf-8')
    message = f"Subject: {asunto}\nMIME-Version: 1.0\nContent-type: text/html\n\n{texto}".encode("utf-8")

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        try:
            # server.ehlo()  # Can be omitted
            server.starttls(context=context)
            # server.ehlo()  # Can be omitted
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)
            enviado = True
        except Exception as e:
            if hasattr(e, 'message'):
                print(e.message)
            else:
                print(e)
        finally:
            server.quit()
    return enviado

def get_estudiantes_con_mas_de_x_dias_sin_conectarse_a_curso(conexion,  dias):
    """
    Devuelve una lista de estudiantes que llevan mas de x días sin conectarse a un curso
    """
    
    print("get_estudiantes_con_mas_de_x_dias_sin_conectarse_a_curso(...)")

    cursor = conexion.cursor()

    sql = '''
        SELECT 
            c.id cid,
            c.fullname,
            u.id uid,
            u.lastname,
            u.firstname ,
            DATE_FORMAT(FROM_UNIXTIME(la.timeaccess), '%d-%m-%Y %H:%i') as ult_acceso, 
            DATE_FORMAT(now(), '%d-%m-%Y %H:%i') as hoy,
            DATEDIFF(DATE_FORMAT(FROM_UNIXTIME(la.timeaccess), '%Y-%m-%d %H:%i'), curdate() ) * (-1) as dias_entre_ult_acceso_y_hoy
        FROM mdl_user_lastaccess la
            join mdl_user as u on u.id = la.userid
            join mdl_course as c on c.id = la.courseid
            join mdl_user_enrolments as ue on ue.userid = u.id
            join mdl_enrol as e  on e.id = ue.enrolid
        where u.username not like 'prof%' 
            and ((DATEDIFF(DATE_FORMAT(FROM_UNIXTIME(la.timeaccess), '%Y-%m-%d %H:%i'), curdate() ) * (-1)) > 10)
            and c.id = e.courseid
            and c.id not in (2, 5)
            and c.fullname not like ('%centros de trabajo%')
            and c.shortname not like '%t'
            and ue.status = 0 -- activo: 0 suspendido: 1
        order by c.id, u.lastname
            '''
    
    cursor.execute(sql)

    resultados = cursor.fetchall()
    
    
    for fila in resultados:
        cid, fullname, uid, lastname, firstname, ult_acceso, hoy, dias_entre_ult_acceso_y_hoy = fila
        print(f"cid: {cid}, fullname: {fullname}, uid: {uid}")

    
    estudiantes = []   
    

    return estudiantes

###################################################
###################################################
###################################################
# Main:
###################################################
###################################################
###################################################

def main():
    # Obtengo la instncia de Moodle con la que voy a trabajar
    conexion = abrir_conexion()

    # Obtengo un listado de usuarios que no hayan entrado a un determinado curso 
    # en 10 días o mas y su nombre de usuario no empiece por prof. El listado 
    # deberá ir ordenado en primer lugar por el curso y en segundo por los apellidos.
    estudiantes = get_estudiantes_con_mas_de_x_dias_sin_conectarse_a_curso(conexion, 10)
    # Recorro el listado de usuarios anterior y aviso por email a cada uno de ellos.
    # Además, mientras sea el mismo curso almaceno en una lista los usuarios avisados y 
    # tras cambiar de curso envío un email al profesor de ese curso con listado 
    # de usuarios avisados
    for estudiante in estudiantes:
        print(estudiante)
        print(estudiante['courseid'])
        print(estudiante['coursename'])
        print(estudiante['userid'])
        print(estudiante['userlastname'])
        print(estudiante['userfirstname'])
        print(estudiante['ultimoacceso'])
        print(estudiante['hoy'])
        print(estudiante['diasentre'])
        print("-------------------------------------------------")
        print("-------------------------------------------------")
        print("-------------------------------------------------")




###################################################
###################################################
###################################################
# Lanzamos!
###################################################
###################################################
###################################################
try:
    main()
except Exception as exc:
    print("1.- traceback.print_exc()")
    traceback.print_exc()
    print("2.- traceback.print_exception(*sys.exc_info())")
    traceback.print_exception(*sys.exc_info())
    print("--------------------")
    print(exc)
    send_email("pruizs@campusdigitalfp.com", "ERROR - Informe automatizado gestión automática usuarios moodle", "Ha fallado el informe, revisar logs. <br/>Error: " + str(exc) + "<br/><br/><br/>" + str(traceback.print_exc()) + "<br/><br/><br/>" + str(traceback.print_exception(*sys.exc_info())))