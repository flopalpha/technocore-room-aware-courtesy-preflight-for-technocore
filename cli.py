'''Command line for room-aware courtesy preflight.'''
import argparse
import json
import sys
import preflight
def load_history(path):
    '''Read a JSON list of seq and text records.'''
    with open(path, 'r', encoding='utf-8') as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError('history file must hold a JSON list')
    clean = []
    for item in data:
        if not isinstance(item, dict):
            continue
        seq = item.get('seq')
        txt = item.get('text')
        if type(seq) is not int:
            continue
        if not isinstance(txt, str):
            continue
        clean.append({'seq': seq, 'text': txt})
    return clean
def parse_args(argv):
    '''Parse command line options.'''
    parser = argparse.ArgumentParser(description='Check room density before posting; advisory only, never sends.')
    parser.add_argument('--history', required=True, help='path to JSON history list')
    parser.add_argument('--draft', required=True, help='draft text to check')
    parser.add_argument('--after-seq', type=int, default=0, help='only use seq above this cursor')
    parser.add_argument('--limit', type=int, default=20, help='max messages to read, capped at 50')
    parser.add_argument('--preview', type=int, default=5, help='how many recent lines to show')
    parser.add_argument('--write-report', default=None, help='optional path to save JSON report')
    return parser.parse_args(argv)
def main(argv=None):
    '''Run preflight check and print advisory.'''
    args = parse_args(argv)
    try:
        capped = int(args.limit)
    except Exception:
        capped = preflight.DEFAULT_LIMIT
    try:
        show = int(args.preview)
    except Exception:
        show = preflight.DEFAULT_PREVIEW
    try:
        cursor = int(args.after_seq)
    except Exception:
        cursor = 0
    try:
        messages = load_history(args.history)
    except FileNotFoundError:
        print('history file not found: ' + str(args.history), file=sys.stderr)
        return 2
    except ValueError as err:
        print('bad history file: ' + str(err), file=sys.stderr)
        return 2
    except Exception as err:
        print('could not read history: ' + str(err), file=sys.stderr)
        return 2
    window = preflight.slice_window(messages, cursor, capped)
    report = preflight.build_report(args.draft, messages, cursor, capped)
    preview = preflight.render_preview(window, args.draft, show)
    print(preview)
    print('')
    print('verdict: ' + str(report['verdict']) + ' (score ' + str(report['courtesy_score']) + '/100)')
    print('reasons:')
    for reason in report['reasons']:
        print('- ' + str(reason))
    print('manual confirm needed: yes - this tool never posts on its own')
    print('seq range: ' + str(report['min_seq']) + ' to ' + str(report['max_seq']) + ' count ' + str(report['count']))
    if args.write_report:
        try:
            text = preflight.report_to_json(report)
            with open(args.write_report, 'w', encoding='utf-8') as handle:
                handle.write(text + chr(10))
            print('saved report to ' + str(args.write_report))
        except Exception as err:
            print('could not save report: ' + str(err), file=sys.stderr)
            return 2
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
