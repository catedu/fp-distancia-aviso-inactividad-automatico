import mysql.connector
import smtplib
import os
import sys
import time
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
    print("abrir_conexion()")

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
    return enviado

def return_text_for_html(cadena):
    """
    Cada una cadena de texto reemplaza los caracteres con tildes por su equivalente en html
    """
    # print("return_text_for_html(",cadena,"). Tipo(", type(cadena) , ")" , sep="")
    cadena = cadena.replace("á", "&aacute;")
    cadena = cadena.replace("é", "&eacute;")
    cadena = cadena.replace("í", "&iacute;")
    cadena = cadena.replace("ó", "&oacute;")
    cadena = cadena.replace("ú", "&uacute;")

    cadena = cadena.replace("Á", "&Aacute;")
    cadena = cadena.replace("É", "&Eacute;")
    cadena = cadena.replace("Í", "&Iacute;")
    cadena = cadena.replace("Ó", "&Oacute;")
    cadena = cadena.replace("Ú", "&Uacute;")

    cadena = cadena.replace("ñ", "&ntilde;")
    cadena = cadena.replace("Ñ", "&Ntilde;")

    return cadena

def return_teacher_of_course(conexion, cid):
    print("return_teacher_of_course(conexion, cid: '" + str(cid) + "')")

    cursor = conexion.cursor()

    sql = f'''
        SELECT
            u.firstname AS first_name,
            u.lastname AS last_name,
            u.email
        FROM
            mdl_user u
        JOIN
            mdl_role_assignments ra ON u.id = ra.userid
        JOIN
            mdl_context ctx ON ra.contextid = ctx.id
        JOIN
            mdl_role r ON ra.roleid = r.id
        WHERE
            ctx.instanceid = {cid} 
            AND r.shortname = 'editingteacher'
        '''
    
    cursor.execute(sql)

    resultados = cursor.fetchall()

    for fila in resultados:
        first_name, last_name, email = fila
        teacher = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email
        }

    return teacher

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

    # Recorro el listado de usuarios anterior y aviso por email a cada uno de ellos.
    # Además, mientras sea el mismo curso almaceno en una lista los usuarios avisados y 
    # tras cambiar de curso envío un email al profesor de ese curso con listado 
    # de usuarios avisados
    estudiantes = []

    cursor = conexion.cursor()

    sql = '''
        SELECT 
            c.id cid,
            c.fullname,
            c.shortname,
            u.id uid,
            u.lastname,
            u.firstname,
            u.email,
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
            and c.shortname like '%125-%' -- solo los del campus
        order by c.id, u.lastname
            '''
    
    cursor.execute(sql)

    resultados = cursor.fetchall()
    
    last_cid = 0
    last_cname = ""
    num_emails_enviados = 0
    num_emails_no_enviados = 0
    
    for fila in resultados:
        #
        cid, fullname, shortname, uid, lastname, firstname, email, ult_acceso, hoy, dias_entre_ult_acceso_y_hoy = fila
        
        # Si estamos de pruebas, enviamos el email a fp@catedu. 
        # Si estamos en produción enviamos un email a quién corresponda
        # Si cambiamos de curso avisamos al profesor del curso cambiado con la relación de estudiantes avisados
        if last_cid != cid:
            if last_cid != 0:
                print(f"----- Enviar email al profesor del curso {last_cid} con el listado de alumnos avisados.")
                teacher = return_teacher_of_course(conexion, last_cid)
                mensaje_teacher = f'''
                    Hola {return_text_for_html(teacher['first_name'])} {return_text_for_html(teacher['last_name'])},<br><br>nos ponemos en contacto con usted para informarle de que se ha enviado un email de aviso de inactividad en el <strong>curso {return_text_for_html(last_cname)}</strong> a los siguientes estudiantes:'''
                for estudiante in estudiantes:
                    print(f"{estudiante} ")
                    mensaje_teacher += f"<br/>{return_text_for_html(estudiante)}"

                mensaje_teacher += f'''<br><br><strong>No responda a esta cuenta de correo electr&oacute;nico pues se trata de una cuenta automatizada no atendida</strong>.<br/><br/><br/>Saludos'''
                destinatario = "fp@catedu.es"
                if SUBDOMAIN == "www":
                    destinatario = teacher['email']
                else:
                    print(f"Debería haberse enviado a 'teacher['email']' pero se enviará a '{destinatario}'" )
                enviado = send_email(destinatario, f"FP a distancia - Avisados de inactividad", mensaje_teacher)

                if enviado:
                    num_emails_enviados = num_emails_enviados + 1
                    print("num_emails_enviados: ", num_emails_enviados)
                else:
                    num_emails_no_enviados = num_emails_no_enviados + 1
                    print("num_emails_no_enviados: ", num_emails_no_enviados)
                    print("No se ha podido enviar el email a: ", destinatario)

                time.sleep(2)
                print(f"")

                estudiantes.clear()
            last_cid = cid
            last_cname = fullname
            print(f"--- Curso ({cid}) - {fullname} ")
        
        # Avisamos al estudiante de que lleva x días sin conectarse al curso
        nombre = return_text_for_html(firstname)
        apellidos = return_text_for_html(lastname)
        nombre_curso = return_text_for_html(fullname)
        mensaje = f'''Hola {nombre} {apellidos},<br><br>nos ponemos en contacto con usted porque su &uacute;ltimo acceso al curso <a href="https://{SUBDOMAIN}.adistanciafparagon.es/course/view.php?id={cid}">{nombre_curso}</a> fue el {ult_acceso} (han transcurrido {dias_entre_ult_acceso_y_hoy} d&iacute;as super&aacute;ndose el m&aacute;ximo de 10 d&iacute;as sin acceder a un curso). Por favor, acceda a la mayor brevedad posible.<br/><br/>Le recomendamos que si no va a continuar con los estudios contacte con su centro para que le indiquen el proceso para solicitar la anulaci&oacute;n y as&iacute; no le corra convocatoria (el n&uacute;mero de convocatorias es limitado).<br/><br/>Puede recuperar su contrase&ntilde;a en cualquier momento a trav&eacute;s de https://{SUBDOMAIN}.adistanciafparagon.es/login/forgot_password.php<br>En caso de cualquier problema consulte con su coordinador/a de ciclo o acuda a la secci&oacute;n de <a href="https://{SUBDOMAIN}.adistanciafparagon.es/soporte/">ayuda/incidencias</a>.<br><br><strong>No responda a esta cuenta de correo electr&oacute;nico pues se trata de una cuenta automatizada no atendida</strong>.<br/><br/><br/>Saludos<br/><br/>'''

        #         
        destinatario = "fp@catedu.es"
        if SUBDOMAIN == "www":
            destinatario = email
        else:
            print(f"Debería haberse enviado a '{email}' pero se enviará a '{destinatario}'" )
        
        # Enviamos el email
        enviado = send_email(destinatario, f"FP a distancia - AVISO de inactividad", mensaje)
        if enviado:
            num_emails_enviados = num_emails_enviados + 1
            print("num_emails_enviados: ", num_emails_enviados)
        else:
            num_emails_no_enviados = num_emails_no_enviados + 1
            print("num_emails_no_enviados: ", num_emails_no_enviados)
            print("No se ha podido enviar el email a: ", destinatario)
        time.sleep(2)
        # Agregamos al listado de estudiantes al que acabamos de avisar para este curso
        estudiantes.append(f"- {firstname} {lastname}")


###################################################
###################################################
###################################################
# Lanzamos!
###################################################
###################################################
###################################################
try:
    print("Lanzando...")
    main()
    print("Fin!")
except Exception as exc:
    print("1.- traceback.print_exc()")
    traceback.print_exc()
    print("2.- traceback.print_exception(*sys.exc_info())")
    traceback.print_exception(*sys.exc_info())
    print("--------------------")
    print(exc)
    send_email("pruizs@campusdigitalfp.com", "ERROR - Avisador inactividad automático Moodle", "Ha fallado el informe, revisar logs. <br/>Error: " + str(exc) + "<br/><br/><br/>" + str(traceback.print_exc()) + "<br/><br/><br/>" + str(traceback.print_exception(*sys.exc_info())))