from typing import Any

from pydantic_core import core_schema
from typing_extensions import Annotated

from pydantic import (
    BaseModel,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
)
from pydantic.json_schema import JsonSchemaValue


class ReactiveList(list):
    def __init__(self, iterable, trigger_callback=None):
        super().__init__(iterable)
        self._trigger_callback = trigger_callback
        # 将嵌套的字典或列表转换为响应式对象
        for i, item in enumerate(self):
            if isinstance(item, dict):
                self[i] = ReactiveDict(item, self._trigger_callback)
            elif isinstance(item, list):
                self[i] = ReactiveList(item, self._trigger_callback)

    def __setitem__(self, key, value):
        # 如果值是字典或列表，包装为响应式对象
        if isinstance(value, dict):
            value = ReactiveDict(value, self._trigger_callback)
        elif isinstance(value, list):
            value = ReactiveList(value, self._trigger_callback)
        super().__setitem__(key, value)
        self._notify()

    def __getitem__(self, key):
        value = super().__getitem__(key)
        # 如果值是字典或列表，确保返回的是响应式对象
        if isinstance(value, dict) and not isinstance(value, ReactiveDict):
            value = ReactiveDict(value, self._trigger_callback)
            self[key] = value
        elif isinstance(value, list) and not isinstance(value, ReactiveList):
            value = ReactiveList(value, self._trigger_callback)
            self[key] = value
        return value

    def __delitem__(self, key):
        super().__delitem__(key)
        self._notify()

    def append(self, value):
        # 如果值是字典或列表，包装为响应式对象
        if isinstance(value, dict):
            value = ReactiveDict(value, self._trigger_callback)
        elif isinstance(value, list):
            value = ReactiveList(value, self._trigger_callback)
        super().append(value)
        self._notify()

    def pop(self, index=-1):
        result = super().pop(index)
        self._notify()
        return result

    def _notify(self):
        # 触发更新
        if self._trigger_callback:
            self._trigger_callback()


class ReactiveDict(dict):
    def __init__(self, mapping, trigger_callback=None):
        super().__init__(mapping)
        self._trigger_callback = trigger_callback
        # 将嵌套的字典或列表转换为响应式对象
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = ReactiveDict(value, self._trigger_callback)
            elif isinstance(value, list):
                self[key] = ReactiveList(value, self._trigger_callback)

    def __setitem__(self, key, value):
        # 如果值是字典或列表，包装为响应式对象
        if isinstance(value, dict):
            value = ReactiveDict(value, self._trigger_callback)
        elif isinstance(value, list):
            value = ReactiveList(value, self._trigger_callback)
        super().__setitem__(key, value)
        self._notify()

    def __getitem__(self, key):
        value = super().__getitem__(key)
        # 如果值是字典或列表，确保返回的是响应式对象
        if isinstance(value, dict) and not isinstance(value, ReactiveDict):
            value = ReactiveDict(value, self._trigger_callback)
            self[key] = value
        elif isinstance(value, list) and not isinstance(value, ReactiveList):
            value = ReactiveList(value, self._trigger_callback)
            self[key] = value
        return value

    def __delitem__(self, key):
        super().__delitem__(key)
        self._notify()

    def _notify(self):
        # 触发更新
        if self._trigger_callback:
            self._trigger_callback()


class Ref:
    def __init__(self, value):
        self._dependencies = set()  # 初始化 _dependencies
        self._value = self._wrap_value(value)

    @property
    def value(self):
        self._track()
        return self._value

    @value.setter
    def value(self, new_value):
        if new_value != self._value:
            self._value = self._wrap_value(new_value)
            self._trigger()

    def _wrap_value(self, value):
        # 如果是列表或字典，包装为响应式对象
        if isinstance(value, list):
            return ReactiveList(value, self._trigger)
        elif isinstance(value, dict):
            return ReactiveDict(value, self._trigger)
        else:
            return value

    def _track(self):
        # 模拟依赖收集
        # print("Tracking dependency...")
        pass

    def _trigger(self):
        # 触发所有依赖回调
        print("Triggering update...")
        for callback in self._dependencies:
            callback()

    def add_dependency(self, callback):
        # 添加依赖回调
        self._dependencies.add(callback)

    def __repr__(self):
        return self._value.__repr__()


# Pydantic ===============================================


class _RefTypePydanticAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:

        def validate_from_any(value: Any) -> Ref:
            result = Ref(value)
            return result

        from_any_schema = core_schema.no_info_plain_validator_function(
            validate_from_any
        )

        return core_schema.json_or_python_schema(
            json_schema=from_any_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(Ref),
                    from_any_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: instance.value
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(core_schema.any_schema())


RefType = Annotated[Ref, _RefTypePydanticAnnotation]
# ========================================================


# 运行所有测试
if __name__ == "__main__":

    # 测试 1: 基本类型（整数）
    def test_primitive():
        print("=== 测试 1: 基本类型（整数） ===")
        count = Ref(0)

        def on_update():
            print(f"Count updated to: {count.value}")

        count.add_dependency(on_update)

        count.value = 1
        # 输出: Triggering update... Count updated to: 1
        count.value += 1
        # 输出: Triggering update... Count updated to: 2
        print()

    # 测试 2: 基本类型（字符串）
    def test_string():
        print("=== 测试 2: 基本类型（字符串） ===")
        name = Ref("Alice")

        def on_update():
            print(f"Name updated to: {name.value}")

        name.add_dependency(on_update)

        name.value = "Bob"
        # 输出: Triggering update... Name updated to: Bob
        print()

    # 测试 3: 列表（嵌套基本类型）
    def test_list_with_primitives():
        print("=== 测试 3: 列表（嵌套基本类型） ===")
        items = Ref([1, 2, 3])

        def on_update():
            print(f"List updated: {items.value}")

        items.add_dependency(on_update)

        items.value.append(4)
        # 输出: Triggering update... List updated: [1, 2, 3, 4]
        items.value[0] = 10
        # 输出: Triggering update... List updated: [10, 2, 3, 4]
        items.value.pop()
        # 输出: Triggering update... List updated: [10, 2, 3]
        print("len: ", len(items.value))
        print()

    # 测试 4: 字典（嵌套基本类型）
    def test_dict_with_primitives():
        print("=== 测试 4: 字典（嵌套基本类型） ===")
        user = Ref({"name": "Alice", "age": 25})

        def on_update():
            print(f"Dict updated: {user.value}")

        user.add_dependency(on_update)

        user.value["age"] = (
            26
            # 输出: Triggering update... Dict updated: {'name': 'Alice', 'age': 26}
        )
        user.value["city"] = (
            "New York"
            # 输出: Triggering update... Dict updated: {'name': 'Alice', 'age': 26, 'city': 'New York'}
        )
        del user.value["city"]
        # 输出: Triggering update... Dict updated: {'name': 'Alice', 'age': 26}
        print()

    # 测试 5: 列表（嵌套字典）
    def test_list_with_dict():
        print("=== 测试 5: 列表（嵌套字典） ===")
        items = Ref([{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}])

        def on_update():
            print(f"List updated: {items.value}")

        items.add_dependency(on_update)

        items.value[0]["age"] += 1
        # 输出: Triggering update... List updated: [{'name': 'Alice', 'age': 26}, {'name': 'Bob', 'age': 30}]
        items.value.append({"name": "Charlie", "age": 35})
        # 输出: Triggering update... List updated: [{'name': 'Alice', 'age': 26}, {'name': 'Bob', 'age': 30}, {'name': 'Charlie', 'age': 35}]
        print()

    # 测试 6: 字典（嵌套列表）
    def test_dict_with_list():
        print("=== 测试 6: 字典（嵌套列表） ===")
        user = Ref({"name": "Alice", "scores": [80, 90, 85]})

        def on_update():
            print(f"Dict updated: {user.value}")

        user.add_dependency(on_update)

        user.value["scores"].append(95)
        # 输出: Triggering update... Dict updated: {'name': 'Alice', 'scores': [80, 90, 85, 95]}
        user.value["scores"][0] = 100
        # 输出: Triggering update... Dict updated: {'name': 'Alice', 'scores': [100, 90, 85, 95]}
        print()

    # 测试 7: 复杂嵌套（字典中嵌套列表，列表中嵌套字典）
    def test_complex_nesting():
        print("=== 测试 7: 复杂嵌套（字典中嵌套列表，列表中嵌套字典） ===")
        data = Ref(
            {
                "users": [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}],
                "metadata": {"total": 2, "timestamp": "2023-10-01"},
            }
        )

        def on_update():
            print(f"Data updated: {data.value}")

        data.add_dependency(on_update)

        data.value["users"][0]["age"] += 1
        # 输出: Triggering update... Data updated: {'users': [{'name': 'Alice', 'age': 26}, {'name': 'Bob', 'age': 30}], 'metadata': {'total': 2, 'timestamp': '2023-10-01'}}
        data.value["metadata"]["total"] += 1
        # 输出: Triggering update... Data updated: {'users': [{'name': 'Alice', 'age': 26}, {'name': 'Bob', 'age': 30}], 'metadata': {'total': 3, 'timestamp': '2023-10-01'}}
        data.value["users"].append({"name": "Charlie", "age": 35})
        # 输出: Triggering update... Data updated: {'users': [{'name': 'Alice', 'age': 26}, {'name': 'Bob', 'age': 30}, {'name': 'Charlie', 'age': 35}], 'metadata': {'total': 3, 'timestamp': '2023-10-01'}}
        print()

    def test_deepcopy():
        print("=== 测试 deepcopy ===")
        import copy

        data = Ref([1, 2, 3])
        data.value.append(4)
        data_copy = copy.deepcopy(data)
        data_copy.value.append(5)
        print(data.value)  # [1, 2, 3, 4]
        print(data_copy.value)  # [1, 2, 3, 4, 5]

    def test_pydantic():
        print("=== 测试 pydantic ===")
        from pydantic import BaseModel

        class User(BaseModel):
            name: RefType
            age: RefType
            friend: RefType = []

        user = User(name="Alice", age=25, friend=[{"name": "Bob", "age": 30}])
        user.age.value += 1
        user.friend.value.append({"name": "Charlie", "age": 35})
        user.friend.value[1]["age"] += 1
        print(user.model_dump_json())

    # ==================================================
    test_primitive()
    test_string()
    test_list_with_primitives()
    test_dict_with_primitives()
    test_list_with_dict()
    test_dict_with_list()
    test_complex_nesting()
    test_deepcopy()
    test_pydantic()
