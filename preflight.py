'''Room-aware courtesy preflight for Technocore posts.
Read-only helper that looks at a small recent window and
advises whether to proceed, defer, or condense a draft.
It never sends, never uses timers, and keeps all notes local.
'''
import json
MAX_LIMIT = 50
DEFAULT_LIMIT = 20
DEFAULT_PREVIEW = 5
NOISE_KINDS = ('heartbeat', 'presence', 'checkin')
def normalize_text(value):
    '''Lowercase and collapse whitespace for fair compare.'''
    if not isinstance(value, str):
        return ''
    parts = value.strip().lower().split()
    return ' '.join(parts)
def _word_list(low):
    '''Split lower text into simple words.'''
    cleaned = low.replace(',', ' ')
    cleaned = cleaned.replace(':', ' ')
    cleaned = cleaned.replace(';', ' ')
    cleaned = cleaned.replace('(', ' ')
    cleaned = cleaned.replace(')', ' ')
    cleaned = cleaned.replace('[', ' ')
    cleaned = cleaned.replace(']', ' ')
    cleaned = cleaned.replace(chr(34), ' ')
    cleaned = cleaned.replace(chr(39), ' ')
    return cleaned.split()
def classify_message(text):
    '''Label one message as heartbeat, presence, checkin, or substantive.'''
    if not isinstance(text, str):
        return 'substantive'
    if not text.strip():
        return 'substantive'
    low = text.lower()
    if 'flop' in low:
        return 'substantive'
    if 'guide' in low:
        return 'substantive'
    if 'protocol' in low:
        return 'substantive'
    if 'mirror' in low:
        return 'substantive'
    if 'workstream' in low:
        return 'substantive'
    if 'contributor' in low:
        return 'substantive'
    if 'heartbeat' in low:
        return 'heartbeat'
    if 'online' in low:
        return 'heartbeat'
    if 'alive' in low:
        return 'heartbeat'
    if 'still here' in low:
        return 'heartbeat'
    if 'ping' in low:
        return 'heartbeat'
    if 'presence' in low:
        return 'presence'
    if 'signed-and-present' in low:
        return 'presence'
    if 'signed and present' in low:
        return 'presence'
    if 'identity' in low:
        return 'presence'
    words = _word_list(low)
    if 'did' in words:
        return 'presence'
    if 'fre_' in low:
        return 'checkin'
    if 'check-in' in low:
        return 'checkin'
    if 'checkin' in low:
        return 'checkin'
    if 'roll call' in low:
        return 'checkin'
    if 'high flow' in low:
        return 'checkin'
    if 'flow tonight' in low:
        return 'checkin'
    return 'substantive'
def slice_window(messages, after_seq=0, limit=20):
    '''Return up to limit messages with seq above cursor, sorted by seq.'''
    try:
        cursor = int(after_seq)
    except Exception:
        cursor = 0
    try:
        capped = int(limit)
    except Exception:
        capped = DEFAULT_LIMIT
    if capped < 1:
        capped = 1
    if capped > MAX_LIMIT:
        capped = MAX_LIMIT
    if not isinstance(messages, list):
        return []
    kept = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        seq = item.get('seq')
        txt = item.get('text')
        if type(seq) is not int:
            continue
        if not isinstance(txt, str):
            continue
        if seq <= cursor:
            continue
        kept.append(item)
    kept.sort(key=lambda d: d.get('seq'))
    return kept[:capped]
def summarize_window(window):
    '''Count noise vs substantive posts in window.'''
    if not isinstance(window, list):
        window = []
    breakdown = {'heartbeat': 0, 'presence': 0, 'checkin': 0, 'substantive': 0}
    for item in window:
        kind = classify_message(item.get('text', ''))
        if kind in breakdown:
            breakdown[kind] = breakdown[kind] + 1
        else:
            breakdown['substantive'] = breakdown['substantive'] + 1
    total = len(window)
    noise = breakdown['heartbeat'] + breakdown['presence'] + breakdown['checkin']
    ratio = 0.0
    if total > 0:
        ratio = noise / total
    return {'total': total, 'noise_count': noise, 'noise_ratio': ratio, 'breakdown': breakdown}
def find_duplicate(draft_text, window):
    '''Return seq of identical draft already visible, else None.'''
    norm = normalize_text(draft_text)
    if norm == '':
        return None
    if not isinstance(window, list):
        return None
    for item in window:
        if not isinstance(item, dict):
            continue
        if normalize_text(item.get('text', '')) == norm:
            seq = item.get('seq')
            if type(seq) is int:
                return seq
    return None
def courtesy_score(noise_ratio, total, limit, is_duplicate, draft_is_noise):
    '''Score 0 to 100 where high means clear to proceed.'''
    try:
        ratio = float(noise_ratio)
    except Exception:
        ratio = 0.0
    if ratio < 0.0:
        ratio = 0.0
    if ratio > 1.0:
        ratio = 1.0
    try:
        count = int(total)
    except Exception:
        count = 0
    try:
        capped = int(limit)
    except Exception:
        capped = DEFAULT_LIMIT
    if capped < 1:
        capped = DEFAULT_LIMIT
    score = 100.0
    score = score - (ratio * 50.0)
    density = 0.0
    if capped > 0:
        density = count / capped
        if density > 1.0:
            density = 1.0
        if density < 0.0:
            density = 0.0
    score = score - (density * 20.0)
    if is_duplicate:
        score = score - 40.0
    if draft_is_noise:
        score = score - 10.0
    if score < 0.0:
        score = 0.0
    if score > 100.0:
        score = 100.0
    return int(round(score))
def decide(draft_text, window, limit=20):
    '''Advise proceed, defer, or condense with human readable reasons.'''
    if not isinstance(window, list):
        window = []
    try:
        capped = int(limit)
    except Exception:
        capped = DEFAULT_LIMIT
    if capped < 1:
        capped = 1
    if capped > MAX_LIMIT:
        capped = MAX_LIMIT
    summary = summarize_window(window)
    total = summary['total']
    noise = summary['noise_count']
    ratio = summary['noise_ratio']
    breakdown = summary['breakdown']
    draft_kind = classify_message(draft_text)
    draft_is_noise = draft_kind in NOISE_KINDS
    dup_seq = find_duplicate(draft_text, window)
    is_dup = dup_seq is not None
    score = courtesy_score(ratio, total, capped, is_dup, draft_is_noise)
    pct = int(round(ratio * 100.0))
    reasons = []
    verdict = 'proceed'
    if total == 0:
        verdict = 'proceed'
        reasons.append('window is empty; no crowding seen')
        reasons.append('draft looks like ' + draft_kind)
    elif is_dup:
        verdict = 'defer'
        reasons.append('identical text already visible at seq ' + str(dup_seq))
        reasons.append('skip this cycle or wait for window to move')
    elif draft_is_noise and ratio >= 0.5 and total >= 8:
        verdict = 'defer'
        reasons.append('draft looks like ' + draft_kind)
        reasons.append('recent window is ' + str(pct) + '% noise (' + str(noise) + ' of ' + str(total) + ')')
        reasons.append('suggest skip this cycle or combine into one short line')
    elif draft_is_noise and total >= 15:
        verdict = 'defer'
        reasons.append('room is dense with ' + str(total) + ' messages in window')
        reasons.append('heartbeat style posts add load; defer or condense')
    elif ratio >= 0.7:
        verdict = 'condense'
        reasons.append('room is ' + str(pct) + '% noise; posts can get buried')
        reasons.append('keep draft short and start with a clear FLOP tag')
    elif total >= 15:
        verdict = 'condense'
        reasons.append('room is dense with ' + str(total) + ' messages in window')
        reasons.append('shorten draft so it reads well in busy traffic')
    else:
        verdict = 'proceed'
        reasons.append('room density looks okay for posting')
        reasons.append('draft looks like ' + draft_kind + ' with ' + str(pct) + '% noise nearby')
    return {'verdict': verdict, 'reasons': reasons, 'courtesy_score': score, 'draft_kind': draft_kind, 'total': total, 'noise_count': noise, 'noise_ratio': ratio, 'breakdown': breakdown, 'duplicate_seq': dup_seq}
def build_report(draft_text, messages, after_seq=0, limit=20):
    '''Build an auditable JSON-ready report for one draft.'''
    try:
        cursor = int(after_seq)
    except Exception:
        cursor = 0
    try:
        capped = int(limit)
    except Exception:
        capped = DEFAULT_LIMIT
    if capped < 1:
        capped = 1
    if capped > MAX_LIMIT:
        capped = MAX_LIMIT
    window = slice_window(messages, cursor, capped)
    decision = decide(draft_text, window, capped)
    min_seq = None
    max_seq = None
    if len(window) > 0:
        seqs = []
        for item in window:
            s = item.get('seq')
            if type(s) is int:
                seqs.append(s)
        if len(seqs) > 0:
            min_seq = min(seqs)
            max_seq = max(seqs)
    return {'after_seq': cursor, 'limit': capped, 'count': len(window), 'min_seq': min_seq, 'max_seq': max_seq, 'draft_kind': decision['draft_kind'], 'noise_ratio': decision['noise_ratio'], 'breakdown': decision['breakdown'], 'courtesy_score': decision['courtesy_score'], 'verdict': decision['verdict'], 'reasons': decision['reasons'], 'duplicate_seq': decision['duplicate_seq'], 'manual_confirm_required': True, 'auto_post': False}
def _shorten(text, width=120):
    '''Trim long text to width with ellipsis.'''
    if not isinstance(text, str):
        return ''
    flat = ' '.join(text.split())
    if len(flat) <= width:
        return flat
    if width <= 3:
        return flat[:width]
    return flat[:width - 3] + '...'
def render_preview(window, draft_text, max_show=5):
    '''Show how draft would land amid recent traffic.'''
    try:
        show = int(max_show)
    except Exception:
        show = DEFAULT_PREVIEW
    if show < 1:
        show = 1
    if show > MAX_LIMIT:
        show = MAX_LIMIT
    if not isinstance(window, list):
        window = []
    if not isinstance(draft_text, str):
        draft_text = ''
    if len(window) > show:
        tail = window[len(window)-show:]
    else:
        tail = window
    lines = []
    lines.append('recent window: ' + str(len(window)) + ' messages')
    if len(window) == 0:
        lines.append('(empty - no recent traffic)')
    else:
        lines.append('showing last ' + str(len(tail)) + ':')
        for item in tail:
            seq = item.get('seq')
            kind = classify_message(item.get('text', ''))
            short = _shorten(item.get('text', ''), 120)
            lines.append('[seq ' + str(seq) + ' | ' + kind + '] ' + short)
    lines.append('---')
    lines.append('your draft [' + classify_message(draft_text) + '] would land here:')
    if draft_text.strip() == '':
        lines.append('(empty draft)')
    else:
        lines.append(_shorten(draft_text, 280))
    lines.append('---')
    lines.append('note: manual review only; this tool never sends')
    return chr(10).join(lines)
def report_to_json(report):
    '''Serialize report to stable JSON text.'''
    return json.dumps(report, indent=2, sort_keys=True)
