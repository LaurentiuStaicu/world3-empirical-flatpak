"""Usage: python3 scripts/audit_egrid.py /path/to/egrid2023_data_rev2.xlsx OUTPUT_DIR

Read-only workbook extraction. Outputs JSON, never modifies the source workbook.
Requires openpyxl. Original file SHA must match the reviewed EPA revision.
"""
from pathlib import Path
import sys,json,hashlib,gzip
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'science/src'),str(ROOT/'science/vendor')]
import openpyxl
from world3_empirical.egrid_audit import audit,FIELDS

def main():
    source=Path(sys.argv[1]); out=Path(sys.argv[2])
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    expected=json.loads((ROOT/'science/data/energy_audit/egrid-source.json').read_text())
    if sha != expected['sha256']:
        raise ValueError('Unreviewed source revision: SHA-256 mismatch')
    w=openpyxl.load_workbook(source,read_only=True,data_only=True)
    rows=w['PLNT23'].iter_rows(values_only=True)
    next(rows); header=next(rows)
    if any(header.count(k)!=1 for k in FIELDS):
        raise ValueError('Missing or duplicate workbook fields')
    report,selected=audit(dict(zip(header,r)) for r in rows if any(v is not None for v in r))
    w.close()
    report['source_sha256']=sha
    report['interpretation']='Source-stratified accounting diagnostic, not independent prediction validation'
    out.mkdir(parents=True,exist_ok=True)
    for name,value in [('egrid-audit.json',report),('egrid-cohort.json',selected)]:
        data=(json.dumps(value,indent=2)+'\n').encode()
        if name == 'egrid-cohort.json':
            name += '.gz'
            data=gzip.compress(data,mtime=0)
        temp=out/(name+'.tmp');temp.write_bytes(data);temp.replace(out/name)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
