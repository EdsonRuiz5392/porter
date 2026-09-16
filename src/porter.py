import sys
import argparse
import subprocess
import sqlite3
import os
import signal

DB_NAME = "porter.db"

def init_db():
    """Inicializa la base de datos de persistencia."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT NOT NULL,
            pid INTEGER,
            status TEXT NOT NULL,
            exit_code INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def main():
    init_db()
    parser = argparse.ArgumentParser(prog='porter', description='Porter JobRunner')
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')

    # porter submit <comando>
    submit_parser = subparsers.add_parser('submit', help='Enviar un nuevo trabajo')
    submit_parser.add_argument('job_command', type=str, help='Comando a ejecutar')

    # porter status <id>
    status_parser = subparsers.add_parser('status', help='Consultar estado')
    status_parser.add_argument('job_id', type=int, help='ID del trabajo')

    # porter list
    subparsers.add_parser('list', help='Listar todos los trabajos')

    # porter cancel <id>
    cancel_parser = subparsers.add_parser('cancel', help='Cancelar trabajo')
    cancel_parser.add_argument('job_id', type=int, help='ID del trabajo')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if args.command == 'submit':
        proc = subprocess.Popen(args.job_command, shell=True)
        cursor.execute(
            "INSERT INTO jobs (command, pid, status, exit_code) VALUES (?, ?, ?, ?)",
            (args.job_command, proc.pid, 'RUNNING', None)
        )
        conn.commit()
        job_id = cursor.lastrowid
        print(f"[+] Trabajo enviado con éxito. ID Único: {job_id} | PID POSIX: {proc.pid}")

    elif args.command == 'status':
        cursor.execute("SELECT id, command, pid, status, exit_code FROM jobs WHERE id = ?", (args.job_id,))
        row = cursor.fetchone()
        if row:
            job_id, cmd, pid, status, exit_code = row
            if status == 'RUNNING':
                poll = subprocess.Popen(f"ps -p {pid}", shell=True, stdout=subprocess.PIPE).wait()
                if poll != 0:
                    status = 'FINISHED'
                    cursor.execute("UPDATE jobs SET status = 'FINISHED' WHERE id = ?", (job_id,))
                    conn.commit()

            print(f"[*] ID: {job_id} | Comando: '{cmd}' | PID: {pid} | Estado: {status}")
        else:
            print(f"[-] Error: No existe el trabajo con ID {args.job_id}")

    elif args.command == 'list':
        cursor.execute("SELECT id, command, pid, status FROM jobs")
        rows = cursor.fetchall()
        print("[*] Trabajos registrados en el sistema:")
        for r in rows:
            print(f"    ID: {r[0]} | Comando: '{r[1]}' | PID: {r[2]} | Estado: {r[3]}")

    elif args.command == 'cancel':
        cursor.execute("SELECT pid, status FROM jobs WHERE id = ?", (args.job_id,))
        row = cursor.fetchone()
        if row and row[1] == 'RUNNING':
            pid = row[0]
            try:
                os.kill(pid, signal.SIGTERM)
                cursor.execute("UPDATE jobs SET status = 'CANCELLED' WHERE id = ?", (args.job_id,))
                conn.commit()
                print(f"[-] Trabajo {args.job_id} (PID {pid}) cancelado mediante SIGTERM.")
            except ProcessLookupError:
                print(f"[-] El proceso {pid} ya no estaba en ejecución.")
        else:
            print(f"[-] El trabajo no se puede cancelar o no existe.")

    conn.close()

if __name__ == '__main__':
    main()