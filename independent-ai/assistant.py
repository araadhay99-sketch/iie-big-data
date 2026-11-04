"""Small local ML assistant. No model download, cloud calls or executable tools."""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from sklearn.pipeline import make_pipeline
from sklearn.svm import LinearSVC

INTENTS = {
    'hello': ['hello', 'hi there', 'good morning', 'hey', 'hello Haven', 'good evening'],
    'identity': ['who are you', 'what are you', 'are you a local AI', 'describe yourself', 'tell me about yourself', 'are you ChatGPT'],
    'help': ['help me', 'what can you do', 'how do I use this', 'how does this work', 'how can you help', 'show your features'],
    'privacy': ['where are my files stored', 'do you send data online', 'is this private', 'does this need internet', 'does my data leave this server', 'can you work offline'],
    'storage': ['how many files do I have', 'show my storage usage', 'how much storage is used', 'is my storage full', 'what is my file count', 'how much free space'],
    'thanks': ['thanks', 'thank you', 'that was helpful', 'much appreciated', 'thank you very much', 'great thanks'],
}

class LocalAssistant:
    def __init__(self):
        examples=[(text,label) for label,phrases in INTENTS.items() for text in phrases]
        self.intent=make_pipeline(TfidfVectorizer(ngram_range=(1,2)),LinearSVC(C=2))
        self.intent.fit([t for t,_ in examples],[label for _,label in examples])

    def retrieve(self, question, passages):
        if not passages:return []
        try:
            model=TfidfVectorizer(stop_words='english',ngram_range=(1,2),sublinear_tf=True,
                                  strip_accents='unicode',max_features=16000)
            matrix=model.fit_transform([p['text'] for p in passages])
            query=model.transform([question])
            if not query.nnz:return []
            scores=linear_kernel(query,matrix).ravel()
        except ValueError:return []
        ranked=sorted(enumerate(scores),key=lambda pair:pair[1],reverse=True)
        found=[];seen=set()
        for index,score in ranked:
            p=passages[index]
            if score<0.14:break
            key=(p['id'],p['text'])
            if key in seen:continue
            found.append({'id':p['id'],'name':p['name'],'excerpt':p['text'][:1300]})
            seen.add(key)
            if len(found)==3:break
        return found

    def respond(self, question, passages, storage):
        sources=self.retrieve(question,passages)
        if sources:
            text='I found these relevant passages in your files. I quote them directly rather than inventing an answer.\n\n'
            text+='\n\n'.join(f"[{i}] {s['name']}\n{s['excerpt']}" for i,s in enumerate(sources,1))
            return text,sources
        values=self.intent.decision_function([question])[0]
        ranked=sorted(zip(values,self.intent.classes_),reverse=True)
        label=ranked[0][1] if ranked[0][0]>.15 and ranked[0][0]-ranked[1][0]>.25 else None
        answers={
            'hello':'Hello. I’m Haven, your local knowledge assistant. Upload a text, Markdown or CSV file, then ask about its contents.',
            'identity':'I’m a small local AI using a trained intent classifier and document relevance model. I run on this server without an external AI API. I’m not a general-purpose language model.',
            'help':'Upload files in Files, then ask a question here. I search supported text files and show relevant passages with sources. Any file type can be stored and downloaded; UTF-8 TXT, Markdown and CSV files can be searched. Move files to Trash to exclude them from answers, or restore them later.',
            'privacy':'Your files, search index and chat history stay in this server’s data folder. This built-in mode makes no external network requests. Server storage is not encrypted by this app; use disk encryption and HTTPS for your own deployment when needed.',
            'storage':f"You have {storage['file_count']} active files and {storage['trash_count']} in Trash. Stored files use {storage['used_bytes']:,} of {storage['quota_bytes']:,} bytes. Trash still counts toward the quota.",
            'thanks':'You’re welcome. Ask about an uploaded file whenever you’re ready.',
        }
        return answers.get(label,'I couldn’t find a relevant passage in your active text files. I answer from your files and a few basic local intents; I don’t browse the internet or generate general-knowledge answers. Try a more specific question or upload a relevant TXT, Markdown or CSV file.'),[]

def split_text(content, limit=64000):
    """Bound indexing work; file storage itself retains the original bytes."""
    text=content[:limit].replace('\r\n','\n')
    paragraphs=re.split(r'\n\s*\n',text)
    result=[]
    for paragraph in paragraphs:
        paragraph=paragraph.strip()
        while paragraph:
            if len(paragraph)<=1100:result.append(paragraph);break
            cut=paragraph.rfind(' ',400,1100)
            if cut<400:cut=1100
            result.append(paragraph[:cut]);paragraph=paragraph[cut:].lstrip()
    return result
