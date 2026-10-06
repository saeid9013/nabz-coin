"""Read an XLSX into private editorial drafts; never publish unreviewed rows."""
import argparse
import json
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def extract(path):
    with zipfile.ZipFile(path) as archive:
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            strings = [''.join(node.itertext()) for node in
                       ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si', NS)]
        def sheet(number):
            result = []
            for row in ET.fromstring(archive.read(f'xl/worksheets/sheet{number}.xml')).findall('m:sheetData/m:row', NS):
                record = {}
                for cell in row.findall('m:c', NS):
                    value, inline = cell.find('m:v', NS), cell.find('m:is', NS)
                    text = value.text if value is not None else ''.join(inline.itertext()) if inline is not None else ''
                    record[re.sub(r'\d+', '', cell.get('r'))] = strings[int(text)] if cell.get('t') == 's' else text
                result.append(record)
            return result[1:]
        return sheet(1), sheet(2), sheet(3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xlsx', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / '.tools/editorial/drafts.json')
    args = parser.parse_args()
    # Drafts may contain fabricated identities and must stay outside the public web root.
    root = Path(__file__).resolve().parents[1] / '.tools'
    if not args.output.resolve().is_relative_to(root.resolve()):
        parser.error('Editorial output must remain inside the ignored .tools directory')
    rows, glossary, mappings = extract(args.xlsx)
    mapping = {row['B']: row for row in mappings}
    drafts, excluded = [], []
    for row in rows:
        if row.get('L', '').startswith('گروه کاری مهندسی'):
            excluded.append({'symbol': row['B'], 'reason': 'Repeated synthetic project template'})
            continue
        identity = mapping.get(row['B'], {}).get('A', '')
        drafts.append({'symbol': row['B'], 'cmc_id_candidate': int(identity) if identity.isdigit() and int(identity) < 900000 else None,
                       'status': 'needs_review', 'source_row': row})
    result = {'source': args.xlsx.name, 'drafts': drafts, 'excluded': excluded,
              'glossary_drafts': glossary, 'notice': 'No draft is approved or publicly published by this importer.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Private drafts: {len(drafts)}; excluded templates: {len(excluded)}; glossary drafts: {len(glossary)}')


if __name__ == '__main__':
    main()
