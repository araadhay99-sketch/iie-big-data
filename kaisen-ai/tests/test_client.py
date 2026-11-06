import json,unittest
from kaisen.client import LocalModel,BackendError

def reply(content=None,calls=None,finish='stop'):
    return {'choices':[{'finish_reason':finish,'message':{'content':content,'tool_calls':calls}}]}
def tool(domain='math',arguments=None,name='run_tool',id='c1'):
    return {'id':id,'function':{'name':name,'arguments':json.dumps({'domain':domain,'arguments':arguments or {'operation':'evaluate','expression':'2+2'}})}}

class LocalProtocolTest(unittest.TestCase):
    def test_uses_actual_tool_result_before_final_answer(self):
        observed=[]
        def transport(payload):
            observed.append(payload)
            return reply(calls=[tool()]) if len(observed)==1 else reply('The calculation gives 4.')
        result=LocalModel(transport=transport).answer('What is 2+2?')
        self.assertEqual(len(result['tool_results']),1)
        self.assertTrue(result['tool_results'][0]['result']['verified'])
        self.assertEqual(observed[1]['messages'][-1]['role'],'tool')
        self.assertNotIn('reasoning_content',observed[1]['messages'][-2])
    def test_rejects_external_backends_and_redirects(self):
        for url in ('https://example.com','http://127.0.0.1@evil.example','http://localhost:8081/evil','http://localhost?secret=x'):
            with self.assertRaises(BackendError):LocalModel(url)
    def test_rejects_unknown_citations_and_truncated_answers(self):
        with self.assertRaises(BackendError):LocalModel(transport=lambda p:reply('According to [S9], this is true.')).answer('Question')
        with self.assertRaises(BackendError):LocalModel(transport=lambda p:reply('Partial...',finish='length')).answer('Question')
    def test_no_arbitrary_tool_and_cycles_are_bounded(self):
        with self.assertRaises(BackendError):LocalModel(transport=lambda p:reply(calls=[tool(name='shell')])).answer('Run code')
        with self.assertRaises(BackendError):LocalModel(max_calls=1,transport=lambda p:reply(calls=[tool()])).answer('Compute')
    def test_tool_rejection_is_evidence_not_fake_success(self):
        calls=[]
        def transport(payload):
            calls.append(payload)
            return reply(calls=[tool(arguments={'operation':'evaluate','expression':'__import__("os")'})]) if len(calls)==1 else reply('That expression is unsupported.')
        result=LocalModel(transport=transport).answer('Calculate this expression')
        self.assertIn('error',result['tool_results'][0]['result'])
    def test_hidden_thinking_is_not_exposed_as_final_answer(self):
        result=LocalModel(transport=lambda p:reply('<think>private scratch text</think>Final answer.')).answer('Question')
        self.assertEqual(result['answer'],'Final answer.')
    def test_malformed_call_id_is_not_executed(self):
        with self.assertRaises(BackendError):LocalModel(transport=lambda p:reply(calls=[tool(id=None)])).answer('Question')

if __name__=='__main__':unittest.main()
