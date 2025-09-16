# cleanup in tasks

## How to run

```
$ python3 -m venv venv
$ pip3 install ../../
$ python3 main.py
debug_log| main start
[{"msg": "1"}]
[{"msg": "2"}]
[{"msg": "act"}]
[{"msg": "4"}]
[{"msg": "cast"}]
[{"msg": "act"}]
[{"msg": "7"}]
[{"msg": "8"}]
[{"msg": "act"}]
[{"msg": "cast"}]
[{"msg": "11"}]
[{"msg": "act"}]
[{"msg": "13"}]
^Cdebug_log| Counter.cleanup: 14
debug_log| FizzBuzz.cleanup
debug_log| Logger.cleanup
debug_log| main end
```

