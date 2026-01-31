from app import app, db, Socio, Predio
import random

def poblar_sistema():
    with app.app_context():
        print("Poblando sistema...")
        for i in range(1, 301):
            # Crear Socio
            nuevo_socio = Socio(
                nombre=f"Socio de Prueba {i}",
                cedula=f"1000{i}",
                telefono=f"300{i:04d}"
            )
            db.session.add(nuevo_socio)
            db.session.flush() # Para obtener el ID del socio

            # Crear Predio vinculado
            nuevo_predio = Predio(
                numero_cuenta=f"CTA-{i:03d}",
                serial_medidor=f"SN-{random.randint(1000, 9999)}",
                sector=random.choice(["Sector Alto", "Sector Bajo", "Centro"]),
                socio_id=nuevo_socio.id
            )
            db.session.add(nuevo_predio)
        
        db.session.commit()
        print("¡Listo! 300 socios y predios creados.")

if __name__ == '__main__':
    poblar_sistema()