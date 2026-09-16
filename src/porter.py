import sys
import argparse

def main():
    parser = argparse.ArgumentParser(
        prog='porter',
        description='Porter JobRunner - Gestión y ejecución de trabajos locales'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')

    # Comando: porter submit <comando>
    submit_parser = subparsers.add_parser('submit', help='Enviar un nuevo trabajo')
    submit_parser.add_argument('job_command', type=str, help='Comando a ejecutar (ej. "sleep 10")')

    # Comando: porter status <id>
    status_parser = subparsers.add_parser('status', help='Consultar el estado de un trabajo')
    status_parser.add_argument('job_id', type=str, help='ID del trabajo')

    # Comando: porter list
    subparsers.add_parser('list', help='Listar todos los trabajos')

    # Comando: porter cancel <id>
    cancel_parser = subparsers.add_parser('cancel', help='Cancelar un trabajo en ejecución')
    cancel_parser.add_argument('job_id', type=str, help='ID del trabajo')

    args = parser.parse_args()

    # Manejo de comandos inválidos o vacíos
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Respuestas de prueba (MOCK)
    if args.command == 'submit':
        print(f'[+] Trabajo enviado exitosamente. ID asignado: job-001')
        print(f'    Comando a ejecutar: {args.job_command}')
    elif args.command == 'status':
        print(f'[*] Estado del trabajo {args.job_id}: EJECUTANDO')
    elif args.command == 'list':
        print('[*] Lista de trabajos:')
        print('    ID: job-001 | Estado: EJECUTANDO | Comando: sleep 10')
    elif args.command == 'cancel':
        print(f'[-] Solicitud de cancelación enviada para el trabajo {args.job_id}')

if __name__ == '__main__':
    main()