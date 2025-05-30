from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector
from datetime import datetime
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import defaultdict
import logging

app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Cambia por tu usuario
    'password': '',  # Cambia por tu contraseña
    'database': 'cira',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'autocommit': True
}

# Configuración de email para gmail cira385srl@gmail.com pass:2605%cira contraseña de app: uqrh qyzu pphr iaoz
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email': 'cira385srl@gmail.com',
    'password': 'uqrh qyzu pphr iaoz'
} 


def get_db_connection():
    """Establece conexión con la base de datos con manejo de errores"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Error conectando a la base de datos: {err}")
        raise

def buscar_cliente(apeynom):
    """Busca un cliente por apellido y nombre"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM cliente WHERE apeynom LIKE %s"
        cursor.execute(query, (f"%{apeynom}%",))
        cliente = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return cliente
    except Exception as e:
        logger.error(f"Error buscando cliente: {e}")
        return None

def crear_cliente(datos):
    """Crea un nuevo cliente en la base de datos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """INSERT INTO cliente (apeynom, direccion, localidad, telefono, aseguradora, email) 
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        
        cursor.execute(query, (
            datos['apeynom'],
            datos['direccion'],
            datos['localidad'],
            datos['telefono'],
            datos['aseguradora'],
            datos['email']
        ))
        
        cliente_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return cliente_id
    except Exception as e:
        logger.error(f"Error creando cliente: {e}")
        raise

def eliminar_presupuesto(id_presu):
    """Elimina un item del presupuesto"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "DELETE FROM presupuesto WHERE id_presu = %s"
        cursor.execute(query, (id_presu,))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error eliminando presupuesto: {e}")
        return False

def agregar_presupuesto(datos):
    """Agrega un item al presupuesto"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Combinar acción + parte + lateral
        parte_completa = f"{datos['accion']} - {datos['partes']} - {datos['lateral']}"
        
        query = """INSERT INTO presupuesto (id_cli, fecha, marca, modelo, patente, parte, importe) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        
        cursor.execute(query, (
            datos['id_cli'],
            datetime.now(),
            datos['marca'],
            datos['modelo'],
            datos['patente'],
            parte_completa,
            datos['importe']
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error agregando presupuesto: {e}")
        return False

def obtener_presupuestos(id_cli, patente=None, fecha=None):
    """Obtiene presupuestos de un cliente filtrados por patente y fecha"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if patente and fecha:
            query = """SELECT * FROM presupuesto 
                       WHERE id_cli = %s AND patente = %s AND DATE(fecha) = DATE(%s)
                       ORDER BY fecha DESC"""
            cursor.execute(query, (id_cli, patente, fecha))
        else:
            query = """SELECT * FROM presupuesto WHERE id_cli = %s ORDER BY fecha DESC"""
            cursor.execute(query, (id_cli,))
        
        presupuestos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return presupuestos
    except Exception as e:
        logger.error(f"Error obteniendo presupuestos: {e}")
        return []

def obtener_presupuestos_cliente(cliente_id):
    """Obtiene todos los presupuestos de un cliente agrupados por patente y fecha"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT p.*, c.apeynom, c.email 
            FROM presupuesto p 
            JOIN cliente c ON p.id_cli = c.id_cli 
            WHERE p.id_cli = %s 
            ORDER BY p.fecha DESC, p.patente
        """
        cursor.execute(query, (cliente_id,))
        presupuestos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Agrupar por patente y fecha
        grupos = defaultdict(list)
        for p in presupuestos:
            fecha_str = p['fecha'].strftime('%Y-%m-%d')
            key = f"{p['patente']} - {fecha_str}"
            grupos[key].append(p)
        
        return dict(grupos), presupuestos[0] if presupuestos else None
    except Exception as e:
        logger.error(f"Error obteniendo presupuestos cliente: {e}")
        return {}, None

def generar_html_presupuesto(cliente_nombre, patente, fecha, items, total):
    """Genera el HTML del presupuesto para el email"""
    items_html = ""
    for item in items:
        items_html += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{item['parte']}</td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">${item['importe']:.2f}</td>
        </tr>
    """
    # Fila adicional al final
    items_html += """
        <tr>
            <td colspan="2" style="padding: 8px; font-style: italic; color: #555;">Más daños a verificar</td>
        </tr>
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th {{ background-color: #f8f9fa; padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6; }}
            td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
            .total {{ background-color: #e9ecef; font-weight: bold; }}
            .footer {{ margin-top: 30px; padding: 20px; background-color: #f8f9fa; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="header" style="background-color: #007bff; color: white; padding: 20px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%;">
                <tr>
                    <td style="width: 100px;">
                        <img src="cid:logo_cira" alt="Logo CIRA" style="width: 200px;">
                    </td>
                    <td style="text-align: left;">
                        <h5 style="margin: 0; font-size: 14px;">PRESUPUESTO AUTOMOTOR</h5>
                        <p style="margin: 0; font-size: 12px;">Dirección: Urquiza 385</p>
                        <p style="margin: 0; font-size: 12px;">Tel: 3364661335</p>
                        <p style="margin: 0; font-size: 12px;">
                        <p style="margin: 0; font-size: 12px;">
                            email: <a href="mailto:cirasrl@hotmail.com" style="color: white; text-decoration: none;">cirasrl@hotmail.com</a>
                        </p>

                    </p>
                    </td>
                </tr>
            </table>
        </div>
        
        <div class="content">
            <h2>Cliente: {cliente_nombre}</h2>
            <p><strong>Vehículo:</strong> {patente}</p>
            <p><strong>Fecha:</strong> {fecha}</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Descripción del Trabajo</th>
                        <th style="text-align: right;">Importe</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                    <tr class="total">
                        <td style="padding: 12px; font-weight: bold;">TOTAL</td>
                        <td style="padding: 12px; text-align: right; font-weight: bold;">${total:.2f}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Gracias por confiar en nuestros servicios</p>
            <p><small>Este presupuesto tiene una validez de 30 días</small></p>
        </div>
    </body>
    </html>
    """
    return html

from email.mime.image import MIMEImage

def enviar_presupuesto_email(cliente_email, cliente_nombre, patente, fecha, items, total):
    """Envía el presupuesto por email con imagen embebida"""
    try:
        msg = MIMEMultipart('related')
        msg['Subject'] = f'Presupuesto - {patente} - {fecha}'
        msg['From'] = EMAIL_CONFIG['email']
        msg['To'] = cliente_email

        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)

        html_content = generar_html_presupuesto(cliente_nombre, patente, fecha, items, total)
        parte_html = MIMEText(html_content, 'html', 'utf-8')
        msg_alternative.attach(parte_html)

        # Ruta al logo
        with open('static/images/logo_cira.png', 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', '<logo_cira>')
            img.add_header('Content-Disposition', 'inline', filename='logo_cira.png')
            msg.attach(img)

        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
            server.send_message(msg)

        return True, "Email enviado correctamente"

    except Exception as e:
        logger.error(f"Error enviando email: {e}")
        return False, f"Error al enviar email: {str(e)}"

# RUTAS
@app.route('/')
def index():
    """Página principal con el formulario"""
    return render_template('index.html')

@app.route('/buscar_cliente', methods=['POST'])
def buscar_cliente_ajax():
    """Busca un cliente via AJAX"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
            
        apeynom = data.get('apeynom')
        if not apeynom:
            return jsonify({'error': 'Apellido y nombre requerido'}), 400
            
        cliente = buscar_cliente(apeynom)
        
        if cliente:
            return jsonify({
                'encontrado': True,
                'cliente': cliente
            })
        else:
            return jsonify({'encontrado': False})
    except Exception as e:
        logger.error(f"Error en buscar_cliente_ajax: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/procesar_formulario', methods=['POST'])
def procesar_formulario():
    """Procesa el formulario principal"""
    try:
        datos = request.form.to_dict()
        cliente = buscar_cliente(datos['apeynom'])
        
        if not cliente:
            id_cliente = crear_cliente(datos)
        else:
            id_cliente = cliente['id_cli']
        
        return redirect(url_for('presupuesto', id_cli=id_cliente))
    except Exception as e:
        logger.error(f"Error procesando formulario: {e}")
        return "Error procesando formulario", 500

@app.route('/presupuesto/<int:id_cli>')
def presupuesto(id_cli):
    """Página del formulario de presupuesto"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM cliente WHERE id_cli = %s", (id_cli,))
        cliente = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not cliente:
            return "Cliente no encontrado", 404
        
        presupuestos = []
        return render_template('presupuesto.html', cliente=cliente, presupuestos=presupuestos)
    except Exception as e:
        logger.error(f"Error en página presupuesto: {e}")
        return "Error interno", 500

@app.route('/obtener_presupuestos', methods=['POST'])
def obtener_presupuestos_ajax():
    """Obtiene presupuestos por AJAX cuando se selecciona patente"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
            
        id_cli = data.get('id_cli')
        patente = data.get('patente')
        fecha = data.get('fecha', datetime.now().date())
        
        presupuestos = obtener_presupuestos(id_cli, patente, fecha)
        total = sum(float(p['importe']) for p in presupuestos)
        
        return jsonify({
            'presupuestos': presupuestos,
            'total': total
        })
    except Exception as e:
        logger.error(f"Error obteniendo presupuestos AJAX: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/agregar_item', methods=['POST'])
def agregar_item():
    try:
        datos = request.get_json()
        print("Datos recibidos:", datos)  # Debug

        if not datos:
            return jsonify({'success': False, 'error': 'No se recibieron datos JSON'}), 400

        campos_requeridos = ['id_cli', 'marca', 'modelo', 'patente', 'accion', 'partes', 'importe']
        for campo in campos_requeridos:
            if not datos.get(campo):
                return jsonify({'success': False, 'error': f'Campo {campo} es requerido'}), 400
        
        try:
            float(datos['importe'])
        except ValueError:
            return jsonify({'success': False, 'error': 'El importe debe ser un número válido'}), 400
        
        success = agregar_presupuesto(datos)
        
        if success:
            return jsonify({'success': True, 'message': 'Item agregado correctamente'})
        else:
            return jsonify({'success': False, 'error': 'Error al agregar el item a la base de datos'}), 500
            
    except Exception as e:
        logger.error(f"Error agregando item: {e}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


@app.route('/eliminar_item', methods=['POST'])
def eliminar_item():
    """Elimina un item del presupuesto"""
    try:
        data = request.get_json()
        
        if not data or 'id_presu' not in data:
            return jsonify({'success': False, 'error': 'ID de presupuesto no proporcionado'}), 400
        
        id_presu = data['id_presu']
        success = eliminar_presupuesto(id_presu)
        
        if success:
            return jsonify({'success': True, 'message': 'Item eliminado correctamente'})
        else:
            return jsonify({'success': False, 'error': 'Error al eliminar item'}), 500
            
    except Exception as e:
        logger.error(f"Error eliminando item: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/consultar_presupuestos')
def consultar_presupuestos():
    """Página para consultar presupuestos"""
    return render_template('consultar_presupuestos.html')

@app.route('/buscar_presupuestos', methods=['POST'])
def buscar_presupuestos():
    """Busca presupuestos de un cliente"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
            
        apeynom = data.get('apeynom')
        if not apeynom:
            return jsonify({'error': 'Apellido y nombre requerido'}), 400
            
        cliente = buscar_cliente(apeynom)
        
        if not cliente:
            return jsonify({'encontrado': False})
        
        presupuestos_agrupados, cliente_info = obtener_presupuestos_cliente(cliente['id_cli'])
        
        return jsonify({
            'encontrado': True,
            'cliente': cliente,
            'presupuestos': presupuestos_agrupados
        })
    except Exception as e:
        logger.error(f"Error buscando presupuestos: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/enviar_presupuesto', methods=['POST'])
def enviar_presupuesto():
    """Envía un presupuesto específico por email"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
            
        cliente_id = data.get('cliente_id')
        patente = data.get('patente')
        fecha = data.get('fecha')
        
        if not all([cliente_id, patente, fecha]):
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener datos del cliente
        cursor.execute("SELECT * FROM cliente WHERE id_cli = %s", (cliente_id,))
        cliente = cursor.fetchone()
        
        # Obtener items del presupuesto
        cursor.execute("""
            SELECT * FROM presupuesto 
            WHERE id_cli = %s AND patente = %s AND DATE(fecha) = %s
            ORDER BY fecha
        """, (cliente_id, patente, fecha))
        items = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not cliente or not items:
            return jsonify({'success': False, 'error': 'No se encontraron datos'})
        
        if not cliente['email']:
            return jsonify({'success': False, 'error': 'Cliente sin email registrado'})
        
        # Calcular total
        total = sum(float(item['importe']) for item in items)
        
        # Enviar email
        exito, mensaje = enviar_presupuesto_email(
            cliente['email'], 
            cliente['apeynom'], 
            patente, 
            fecha, 
            items, 
            total
        )
        
        return jsonify({'success': exito, 'message': mensaje})
        
    except Exception as e:
        logger.error(f"Error enviando presupuesto: {e}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    #app.run(debug=True)