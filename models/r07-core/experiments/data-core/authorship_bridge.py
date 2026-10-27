"""Pure authored demonstration composed only from public DATA jobs.

This module does not import the DATA engine/oracle. A caller supplies a runner
(raw_job, budget) -> observation. The Python coordinator, its branching and the
per-job budget reset are outside the language/runtime conformance claim.
"""
from copy import deepcopy

PROFILE_REVISION = 'data-core/r07-v1'
CODEC_REVISION = 'data-wire/r07-v1'
JOB_BUDGET = 65536


def nominal(name):
    return {'tag': 'nominal', 'id': name, 'revision': '1', 'args': []}


def seq(item):
    return {'tag': 'seq', 'item': item}


def mapping(key, value):
    return {'tag': 'map', 'key': key, 'value': value}


def val(typ, payload):
    return {'type': deepcopy(typ), 'data': deepcopy(payload)}


PERSON = nominal('PersonId')
ARTICLE_ID = nominal('ArticleId')
ARTICLE = nominal('Article')
LEGACY = nominal('LegacyArticle')
SCHEMAS = [
    {'id': 'PersonId', 'revision': '1', 'kind': 'record', 'type_params': [],
     'codec': CODEC_REVISION, 'fields': [{'id': 'value', 'type': 'String'}]},
    {'id': 'ArticleId', 'revision': '1', 'kind': 'record', 'type_params': [],
     'codec': CODEC_REVISION, 'fields': [{'id': 'value', 'type': 'String'}]},
    {'id': 'LegacyArticle', 'revision': '1', 'kind': 'record', 'type_params': [],
     'codec': CODEC_REVISION,
     'fields': [{'id': 'id', 'type': ARTICLE_ID}, {'id': 'author', 'type': PERSON}]},
    {'id': 'Article', 'revision': '1', 'kind': 'record', 'type_params': [],
     'codec': CODEC_REVISION,
     'fields': [{'id': 'id', 'type': ARTICLE_ID},
                {'id': 'author_ids', 'type': seq(PERSON)}]},
]


class BridgeStop(Exception):
    def __init__(self, result):
        self.result = result
        super().__init__(result['code'])


def _shape(people, articles):
    def identifier(s):
        return type(s) is str and 0 < len(s) <= 128 and all(
            not 0xD800 <= ord(c) <= 0xDFFF for c in s)
    if type(people) is not list or type(articles) is not list:
        return False
    if len(people) > 32 or len(articles) > 32 or not all(identifier(p) for p in people):
        return False
    for a in articles:
        if type(a) is not dict or set(a) not in (
                {'article_id', 'author_ids'}, {'article_id', 'author_id'}):
            return False
        if not identifier(a['article_id']):
            return False
        if 'author_id' in a:
            if not identifier(a['author_id']):
                return False
        elif (type(a['author_ids']) is not list or len(a['author_ids']) > 16
              or not all(identifier(x) for x in a['author_ids'])):
            return False
    return True


def run_bridge(people, articles, runner):
    """Return full job receipts and typed final data, or a precise rejection.

    Error order: input shape; duplicate people; duplicate article IDs;
    per input article: empty authors, duplicate author, unknown person.
    Index includes every supplied person, even those with no articles.
    """
    jobs = []
    if not _shape(people, articles):
        return {'status': 'InputRejected', 'code': 'INVALID_BRIDGE_INPUT',
                'value': None, 'jobs': jobs}
    people, articles = deepcopy(people), deepcopy(articles)

    def call(role, op, **fields):
        raw = {'source_id': 'authorship/' + str(len(jobs)) + '/' + role,
               'revision': '1', 'profile_revision': PROFILE_REVISION,
               'schemas': deepcopy(SCHEMAS),
               'operation': {'op': op, **deepcopy(fields)}}
        observation = runner(deepcopy(raw), JOB_BUDGET)
        jobs.append({'role': role, 'job': raw, 'observation': deepcopy(observation)})
        if observation['termination'] != 'RETURNED':
            raise BridgeStop({'status': 'JobStopped', 'code': observation['code'],
                              'value': None, 'jobs': jobs})
        return deepcopy(observation['value'])

    def reject(code, **details):
        raise BridgeStop({'status': 'Rejected', 'code': code, 'value': None,
                          'details': details, 'jobs': jobs})

    def unwrap_ok(v, error_code, **details):
        if v['data']['tag'] == 'Err':
            reject(error_code, error=deepcopy(v['data']['value']), **details)
        if v['data']['tag'] != 'Ok':
            raise AssertionError('Result tag invariant')
        return val(v['type']['ok'], v['data']['value'])

    def wrapper(role, typ, text):
        return call(role, 'record', type=typ,
                    fields=[{'id': 'value', 'value': val('String', text)}])

    try:
        person_values = [wrapper('person-' + str(i), PERSON, name)
                         for i, name in enumerate(people)]
        persons = unwrap_ok(call('people-map', 'map_build', key_type=PERSON,
                                 value_type='Unit',
                                 entries=[{'key': p, 'value': val('Unit', None)}
                                          for p in person_values]),
                            'DUPLICATE_PERSON')
        constructed = []
        original_authors = []
        for i, a in enumerate(articles):
            aid = wrapper('article-id-' + str(i), ARTICLE_ID, a['article_id'])
            if 'author_id' in a:
                old_person = wrapper('legacy-person-' + str(i), PERSON, a['author_id'])
                old = call('legacy-record-' + str(i), 'record', type=LEGACY,
                           fields=[{'id': 'id', 'value': aid},
                                   {'id': 'author', 'value': old_person}])
                old_person = call('legacy-author-' + str(i), 'field',
                                  record=old, field='author')
                aid = call('legacy-id-' + str(i), 'field', record=old, field='id')
                authored = [old_person]
            else:
                authored = [wrapper('author-' + str(i) + '-' + str(j), PERSON, name)
                            for j, name in enumerate(a['author_ids'])]
            authors = call('authors-sequence-' + str(i), 'sequence',
                           item_type=PERSON, items=authored)
            article = call('article-record-' + str(i), 'record', type=ARTICLE,
                           fields=[{'id': 'id', 'value': aid},
                                   {'id': 'author_ids', 'value': authors}])
            constructed.append((aid, article, authors))
            original_authors.append(authored)
        article_map = unwrap_ok(call('articles-map', 'map_build', key_type=ARTICLE_ID,
                                     value_type=ARTICLE,
                                     entries=[{'key': aid, 'value': article}
                                              for aid, article, _ in constructed]),
                                'DUPLICATE_ARTICLE')
        # Validation follows original article order, not the newly sorted map.
        for i, (_, article, _) in enumerate(constructed):
            authors = call('validate-authors-field-' + str(i), 'field',
                           record=article, field='author_ids')
            length = call('validate-length-' + str(i), 'length', value=authors)
            if length['data'] == 0:
                reject('EMPTY_AUTHORS', article_index=i)
            author_set = unwrap_ok(call('validate-unique-' + str(i), 'map_build',
                                       key_type=PERSON, value_type='Unit',
                                       entries=[{'key': p, 'value': val('Unit', None)}
                                                for p in original_authors[i]]),
                                   'DUPLICATE_AUTHOR', article_index=i)
            # The set is an ordinary typed result; it is not the author order.
            assert author_set['type'] == mapping(PERSON, 'Unit')
            for j in range(length['data']):
                opt = call('validate-get-' + str(i) + '-' + str(j), 'seq_get',
                           sequence=authors, index=val('Int64', j))
                if opt['data']['tag'] != 'Some':
                    raise AssertionError('validated sequence length invariant')
                person = val(PERSON, opt['data']['value'])
                known = call('validate-known-' + str(i) + '-' + str(j), 'map_get',
                             map=persons, key=person)
                if known['data']['tag'] == 'None':
                    reject('UNKNOWN_PERSON', article_index=i, author_index=j)
        # Rebuild all supplied-person index entries from canonical article order.
        # Control flow/transport iteration is Python orchestration, not a V1 AST.
        index_entries = []
        for pi, pair in enumerate(persons['data']):
            person = val(PERSON, pair['key'])
            aids = call('index-empty-' + str(pi), 'sequence', item_type=ARTICLE_ID,
                        items=[])
            for ai, apair in enumerate(article_map['data']):
                article = val(ARTICLE, apair['value'])
                authors = call('index-authors-' + str(pi) + '-' + str(ai), 'field',
                               record=article, field='author_ids')
                members = unwrap_ok(call('index-members-' + str(pi) + '-' + str(ai),
                                         'map_build', key_type=PERSON, value_type='Unit',
                                         entries=[{'key': val(PERSON, data),
                                                   'value': val('Unit', None)}
                                                  for data in authors['data']]),
                                    'INTERNAL_DUPLICATE_AFTER_VALIDATION')
                found = call('index-contains-' + str(pi) + '-' + str(ai), 'map_get',
                             map=members, key=person)
                if found['data']['tag'] == 'Some':
                    aid = call('index-article-id-' + str(pi) + '-' + str(ai), 'field',
                               record=article, field='id')
                    aids = call('index-append-' + str(pi) + '-' + str(ai), 'seq_append',
                                sequence=aids, value=aid)
            index_entries.append({'key': person, 'value': aids})
        index = unwrap_ok(call('index-map', 'map_build', key_type=PERSON,
                               value_type=seq(ARTICLE_ID), entries=index_entries),
                          'INTERNAL_DUPLICATE_INDEX')
        encoded = {}
        for name, original in [('articles', article_map), ('index', index)]:
            wire = call('encode-' + name, 'encode', value=original)
            decoded = unwrap_ok(call('decode-' + name, 'decode', type=original['type'],
                                     bytes=wire), 'INTERNAL_CODEC_ROUNDTRIP')
            same = call('equal-' + name, 'equal', left=original, right=decoded)
            if same['data'] is not True:
                raise AssertionError('codec changed semantic value')
            encoded[name] = wire
        return {'status': 'Completed', 'code': 'OK',
                'value': {'articles': article_map, 'index': index, 'encoded': encoded},
                'jobs': jobs}
    except BridgeStop as stop:
        return stop.result


def domain_view(result):
    """Human/authored comparison view, not a substitute for the full receipts."""
    if result['status'] != 'Completed':
        return {'status': result['status'], 'code': result['code']}
    v = result['value']
    return {'status': 'Completed', 'code': 'OK',
            'articles': [[p['key']['value'],
                          [a['value'] for a in p['value']['author_ids']]]
                         for p in v['articles']['data']],
            'index': [[p['key']['value'], [a['value'] for a in p['value']]]
                      for p in v['index']['data']]}
