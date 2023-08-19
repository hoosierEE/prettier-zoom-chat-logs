'''make zoom chat text files into prettier html files

usage:
  python3 pretty.py filename.txt > filename.html
'''
import argparse,re

def parse(t):
    pat = re.compile(r'\n[0-9]{2}:[0-9]{2}:[0-9]{2}', re.UNICODE)
    times = re.findall(pat, t)
    stamps = []
    auth = []
    msgs = []
    reacts = {}
    for i in range(1,len(times)):
        t0 = times[i-1]
        t1 = times[i]
        start = t.index(t0)
        t = t[start+9:]
        end = t.index(t1)
        _,author,msg = t[:end].split('\t')

        # fix punctuation
        author = author[:-1]
        t0 = t0[1:]

        # collect reactions
        if msg.startswith('Reacted to "'):
            orig,what = msg[12:].split('" with ')
            if orig.endswith('...'):
                orig = orig[:-3]
            if orig not in reacts:
                reacts[orig] = {what:[author]}
            else:
                reacts[orig][what] = reacts[orig].get(what, []) + [author]

        else:
            stamps.append(t0[1:])
            auth.append(author)
            msgs.append({'text':msg})

    assert len(stamps)==len(auth)==len(msgs), "Parse error"
    return stamps,auth,msgs,reacts


def reply_react(msgs,reacts):
    '''accumulate reply and reaction data in message dict'''
    for i,m in enumerate(msgs):
        msg = m['text']
        for r in reacts:
            if msg.startswith(r):
                m['reactions'] = reacts[r]

        if msg.startswith('Replying to "'):
            splitidx = msg.index('\n')
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
    _id = f' id="{i}"' if i else ''
    return f'<span class="{c}"{_id}>{x}</span>'


def anchor(c,destination,*args):
    return f'<a class="{c}" href="{destination}">{"".join(args)}</a>'


def linkify(s):
    links = re.findall('https://[^ \n\t]+', s)
    for l in links:
        s = s.replace(l, f'<a href="{l}">{l}</a>')
    return s


def tohtml(filename,stamps,auth,msgs,reacts):
    msgs = reply_react(msgs,reacts)
    content = []
    for i,(time,author,msg) in enumerate(zip(stamps,auth,msgs)):
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
        container.append(div('post', span('time',time), span('auth',author), span('msg',text,uid)))

        # add optional reaction emoji and their authors
        if 'reactions' in msg:
            emojos = []
            for k,v in msg['reactions'].items():
                emojos.append(' '.join([k,*v]))

            container.append(div('post', span('time',''), span('auth',''), span('emoj',' '.join(emojos))))

        content.append(div('container', *container))

    content = '\n'.join(content)
    filename = filename.split('/')[-1].split('.txt')[0]
    with open('main.css') as f:
        style = f.read()

    return f'''
<!DOCTYPE html>
<html lang="en-US">
 <head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{filename}</title>
<style>{style}</style>
 </head>
<body>
    <h1>{filename}</h1>
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
    p.add_argument('txt', help='chat log text file (.txt)')
    args = p.parse_args()

    with open(args.txt) as f:
        t = '\n'+f.read()

    html = tohtml(args.txt, *parse(t))
    print(html)
