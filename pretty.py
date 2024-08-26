'''make zoom chat text files into prettier html files'''
import argparse,re,sys


def normalize_ellipsis(message:str) -> str:
    '''replace "..." at end of message with "…"'''
    if message.endswith('...'):
        return message[:-3]+'…'
    return message


def parse(t:str) -> (list[str], list[str], list[dict], list[bool]):
    auths,msgs,times = [],[],re.findall(r'[0-9]{1,2}:[0-9]{2}:[0-9]{2}', t)
    reacts = {}
    for i in range(1,len(times)):
        t0,t1 = times[i-1],times[i]
        t = t[t.index(t0)+8:]
        msg = t[:t.index(t1)].lstrip()  # current message

        # NOTE:
        # Some Zoom chat log outputs are tab-delimited like
        #     00:00:00\tAuthor:\tmessage\r\n
        # Others have a different format (with optional " to Recipient" part and a space-delimited colon):
        #     00:00:00\tFrom Author [ to Recipient(privately)] : message\n
        author,msg = msg.split(':',1)  # split at first colon
        msg = msg.strip()
        if author.startswith('From '):
            author = author[5:]
        author,*rcpt = author.split('  To  ',1)  # at most one(?) recipient
        private = ' '.join(rcpt).endswith('(privately)')

        # add reaction
        if msg.startswith('Reacted to "'):
            orig,what = msg[12:].split('" with ')
            orig = normalize_ellipsis(orig)
            if orig not in reacts:
                reacts[orig] = {what:[author]}
            else:
                reacts[orig][what] = reacts[orig].get(what, []) + [author]

        # remove reaction
        elif what := re.search(r'Removed a (.) reaction from "', msg):
            what = what.groups()[0]
            orig = re.search(r'"(.*)"', msg).groups()[0]
            orig = normalize_ellipsis(orig)
            reacts[orig][what].remove(author)
            if len(reacts[orig][what]) == 0:
                del reacts[orig][what]
            if reacts[orig] == {}:
                del reacts[orig]

        # normal message
        else:
            auths.append(author)
            msgs.append({'text':msg, 'priv':private})

    return times,auths,msgs,reacts


def reply_react(msgs:list[dict], reacts:dict) -> list[dict]:
    '''accumulate reply and reaction data in message dict'''
    for i,m in enumerate(msgs):
        msg = m['text']
        for r in reacts:
            if msg.startswith(r):
                m['reactions'] = reacts[r]

        if msg.startswith('Replying to "'):
            splitidx = len(msg.splitlines()[0])
            orig,what = msg[13:splitidx-1], msg[splitidx:].strip()
            if orig.endswith('...'):
                orig = orig[:-3]

            for j,ms in enumerate(msgs[:i]):
                if ms['text'].startswith(orig):
                    m['replyto'] = j

            m['text'] = what

    return msgs


def div(c,*args):
    return f'<div class="{c}">{"".join(args)}</div>'


def span(c,x,i=None):
    ident = f' id="{i}"' if i else ''
    return f'<span class="{c}"{ident}>{x}</span>'


def anchor(c,destination,*args):
    return f'<a class="{c}" href="{destination}">{"".join(args)}</a>'


def linkify(s):
    for l in re.findall('https://[^ \n\t]+', s):
        s = s.replace(l, f'<a href="{l}">{l}</a>')
    return s


def tohtml(args:argparse.Namespace, stamps:list[str], auth:list[str], msgs:list[dict], reacts:dict) -> str:
    msgs = reply_react(msgs,reacts)
    content = []
    for i,(time,author,msg) in enumerate(zip(stamps,auth,msgs)):
        if msg['priv'] and not args.show_dms:
            continue

        uid = f'id_{i}'
        container = []

        # add optional reply with linkback
        if 'replyto' in msg:
            mid = msg['replyto']
            old = msgs[mid]['text'][:30]+'...'
            container.append(div('post',
                                 span('time',''),
                                 span('author',''),
                                 span('msg', anchor('replylink', f'#id_{mid}', '@'+auth[mid]+' ← '+old))))

        # add main post body
        text = linkify(msg['text'])
        text = text.replace('\n', '<br/>')
        container.append(div('post', span('time',time), span('auth',author), span('msg',text,uid)))

        # add optional reaction emoji and their authors
        if 'reactions' in msg:
            emojos = []
            for k,v in msg['reactions'].items():
                emojos.append(' '.join([k,*v]))

            container.append(div('post', span('time',''), span('auth',''), span('emoj',' '.join(emojos))))

        content.append(div('container', *container))

    content = '\n'.join(content)
    with open('main.css') as f:
        style = f.read()

    return f'''
<!DOCTYPE html>
<html lang="en-US">
 <head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{args.title}</title>
<style>{style}</style>
 </head>
<body>
    <h1>{args.title}</h1>
    <hr>
{content}
    <hr>
    <br>
    <br>
</body>
</html>
'''


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('filenames', nargs='+', metavar='FILE', help='chat log text files, in sorted order')
    p.add_argument('-t', '--title', default='Chat', help='title of resulting document')
    p.add_argument('--show-dms', action='store_true', help='include private messages in generated output')
    args = p.parse_args()

    t = ''
    for filename in args.filenames:
        with open(filename) as f:
            t += f.read() #add tokens to start and end so processing can be uniform

    t += '00:00:00'  # dummy timestamp
    data = parse(t)
    html = tohtml(args, *data)
    print(html)
