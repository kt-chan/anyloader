curl -X 'POST' \
    'http://10.64.142.35:18888/search_chunks' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{
    "query": "the Curriculum requirements of BAsC(SDS)",
    "tag_filters": {
        "exact": {
            "faculty": "faculty_of_education",
            "academic_year": "2024-2025"
        }
    },
    "rerank": true,
    "score_threshold": 0,
    "use_sparse": true
}'
