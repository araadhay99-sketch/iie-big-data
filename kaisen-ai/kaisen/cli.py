import argparse,json,os,sys
from pathlib import Path
from importlib.resources import files
from .tools import run_tool,ToolError
from .budget import Budget,BudgetError
from .archive import Archive
from .model import load_manifest,model_status,install_model,ModelError
from .client import LocalModel,BackendError
from .server import server_command

ROOT=Path.cwd()
def main(argv=None):
    parser=argparse.ArgumentParser(description='Kaisen: computational science groundwork; local reasoning model requires separate installation.')
    parser.add_argument('--root',type=Path,default=ROOT)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('status');commands.add_parser('download-model');commands.add_parser('serve')
    tool=commands.add_parser('tool');tool.add_argument('domain',choices=['math','physics','chemistry','biology','computers']);tool.add_argument('arguments',help='JSON operation arguments')
    ingest=commands.add_parser('ingest');ingest.add_argument('path',type=Path)
    search=commands.add_parser('search');search.add_argument('question')
    chat=commands.add_parser('chat');chat.add_argument('question');chat.add_argument('--server',default='http://127.0.0.1:8081')
    args=parser.parse_args(argv);root=args.root.resolve()
    try:
        if args.command=='tool':result=run_tool(args.domain,json.loads(args.arguments))
        elif args.command in ('status','download-model','serve'):
            manifest=load_manifest(files('kaisen').joinpath('model-manifest.json'));budget=Budget(root)
            if args.command=='serve':
                command=server_command(root,manifest);environment=os.environ.copy()
                for name in ('PA_API_TOKEN','PA_USERNAME'):environment.pop(name,None)
                os.execve(command[0],command,environment)
            if args.command=='download-model':result=install_model(root,manifest,budget=budget)
            else:
                record_path=budget.safe_path('runtime/installed.json')
                record=json.loads(record_path.read_text()) if record_path.is_file() else {}
                result={'model':model_status(root,manifest),'runtime_installed':bool(record.get('runtime_smoke_verified')),'inference_verified':False,'project_bytes':budget.used_bytes(),'project_limit_bytes':20_000_000_000,'petabyte_cloud_allocated':False,'persistent_model_host_verified':False}
        else:
            archive=Archive(root)
            try:
                if args.command=='ingest':result=archive.ingest(args.path)
                elif args.command=='search':result=archive.search(args.question)
                else:result=LocalModel(args.server).answer(args.question,archive.search(args.question))
            finally:
                close=getattr(archive,'close',None)
                if close:close()
        print(json.dumps(result,indent=2,ensure_ascii=False));return 0
    except (ToolError,BudgetError,ModelError,BackendError,ValueError,OSError) as error:
        result=error.to_dict() if isinstance(error,ToolError) else {'error':str(error)}
        print(json.dumps(result),file=sys.stderr);return 2
