import enum
from typing import Any, List

from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema, BlockType
from backend.data.model import SchemaField
from backend.util import json
from backend.util.file import store_media_file
from backend.util.mock import MockObject
from backend.util.type import MediaFileType, convert


class FileStoreBlock(Block):
    class Input(BlockSchema):
        file_in: MediaFileType = SchemaField(
            description="The file to store in the temporary directory, it can be a URL, data URI, or local path."
        )
        base_64: bool = SchemaField(
            description="Whether produce an output in base64 format (not recommended, you can pass the string path just fine accross blocks).",
            default=False,
            advanced=True,
            title="Produce Base64 Output",
        )

    class Output(BlockSchema):
        file_out: MediaFileType = SchemaField(
            description="The relative path to the stored file in the temporary directory."
        )

    def __init__(self):
        super().__init__(
            id="cbb50872-625b-42f0-8203-a2ae78242d8a",
            description="Stores the input file in the temporary directory.",
            categories={BlockCategory.BASIC, BlockCategory.MULTIMEDIA},
            input_schema=FileStoreBlock.Input,
            output_schema=FileStoreBlock.Output,
            static_output=True,
        )

    async def run(
        self,
        input_data: Input,
        *,
        graph_exec_id: str,
        **kwargs,
    ) -> BlockOutput:
        yield "file_out", await store_media_file(
            graph_exec_id=graph_exec_id,
            file=input_data.file_in,
            return_content=input_data.base_64,
        )


class StoreValueBlock(Block):
    """
    This block allows you to provide a constant value as a block, in a stateless manner.
    The common use-case is simply pass the `input` data, it will `output` the same data.
    The block output will be static, the output can be consumed multiple times.
    """

    class Input(BlockSchema):
        input: Any = SchemaField(
            description="Trigger the block to produce the output. "
            "The value is only used when `data` is None."
        )
        data: Any = SchemaField(
            description="The constant data to be retained in the block. "
            "This value is passed as `output`.",
            default=None,
        )

    class Output(BlockSchema):
        output: Any = SchemaField(description="The stored data retained in the block.")

    def __init__(self):
        super().__init__(
            id="1ff065e9-88e8-4358-9d82-8dc91f622ba9",
            description="This block forwards an input value as output, allowing reuse without change.",
            categories={BlockCategory.BASIC},
            input_schema=StoreValueBlock.Input,
            output_schema=StoreValueBlock.Output,
            test_input=[
                {"input": "Hello, World!"},
                {"input": "Hello, World!", "data": "Existing Data"},
            ],
            test_output=[
                ("output", "Hello, World!"),  # No data provided, so trigger is returned
                ("output", "Existing Data"),  # Data is provided, so data is returned.
            ],
            static_output=True,
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        yield "output", input_data.data or input_data.input


class PrintToConsoleBlock(Block):
    class Input(BlockSchema):
        text: Any = SchemaField(description="The data to print to the console.")

    class Output(BlockSchema):
        output: Any = SchemaField(description="The data printed to the console.")
        status: str = SchemaField(description="The status of the print operation.")

    def __init__(self):
        super().__init__(
            id="f3b1c1b2-4c4f-4f0d-8d2f-4c4f0d8d2f4c",
            description="Print the given text to the console, this is used for a debugging purpose.",
            categories={BlockCategory.BASIC},
            input_schema=PrintToConsoleBlock.Input,
            output_schema=PrintToConsoleBlock.Output,
            test_input={"text": "Hello, World!"},
            test_output=[
                ("output", "Hello, World!"),
                ("status", "printed"),
            ],
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        yield "output", input_data.text
        yield "status", "printed"


class FindInDictionaryBlock(Block):
    class Input(BlockSchema):
        input: Any = SchemaField(description="Dictionary to lookup from")
        key: str | int = SchemaField(description="Key to lookup in the dictionary")

    class Output(BlockSchema):
        output: Any = SchemaField(description="Value found for the given key")
        missing: Any = SchemaField(
            description="Value of the input that missing the key"
        )

    def __init__(self):
        super().__init__(
            id="0e50422c-6dee-4145-83d6-3a5a392f65de",
            description="Lookup the given key in the input dictionary/object/list and return the value.",
            input_schema=FindInDictionaryBlock.Input,
            output_schema=FindInDictionaryBlock.Output,
            test_input=[
                {"input": {"apple": 1, "banana": 2, "cherry": 3}, "key": "banana"},
                {"input": {"x": 10, "y": 20, "z": 30}, "key": "w"},
                {"input": [1, 2, 3], "key": 1},
                {"input": [1, 2, 3], "key": 3},
                {"input": MockObject(value="!!", key="key"), "key": "key"},
                {"input": [{"k1": "v1"}, {"k2": "v2"}, {"k1": "v3"}], "key": "k1"},
            ],
            test_output=[
                ("output", 2),
                ("missing", {"x": 10, "y": 20, "z": 30}),
                ("output", 2),
                ("missing", [1, 2, 3]),
                ("output", "key"),
                ("output", ["v1", "v3"]),
            ],
            categories={BlockCategory.BASIC},
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        obj = input_data.input
        key = input_data.key

        if isinstance(obj, str):
            obj = json.loads(obj)

        if isinstance(obj, dict) and key in obj:
            yield "output", obj[key]
        elif isinstance(obj, list) and isinstance(key, int) and 0 <= key < len(obj):
            yield "output", obj[key]
        elif isinstance(obj, list) and isinstance(key, str):
            if len(obj) == 0:
                yield "output", []
            elif isinstance(obj[0], dict) and key in obj[0]:
                yield "output", [item[key] for item in obj if key in item]
            else:
                yield "output", [getattr(val, key) for val in obj if hasattr(val, key)]
        elif isinstance(obj, object) and isinstance(key, str) and hasattr(obj, key):
            yield "output", getattr(obj, key)
        else:
            yield "missing", input_data.input


class AddToDictionaryBlock(Block):
    class Input(BlockSchema):
        dictionary: dict[Any, Any] = SchemaField(
            default_factory=dict,
            description="The dictionary to add the entry to. If not provided, a new dictionary will be created.",
        )
        key: str = SchemaField(
            default="",
            description="The key for the new entry.",
            placeholder="new_key",
            advanced=False,
        )
        value: Any = SchemaField(
            default=None,
            description="The value for the new entry.",
            placeholder="new_value",
            advanced=False,
        )
        entries: dict[Any, Any] = SchemaField(
            default_factory=dict,
            description="The entries to add to the dictionary. This is the batch version of the `key` and `value` fields.",
            advanced=True,
        )

    class Output(BlockSchema):
        updated_dictionary: dict = SchemaField(
            description="The dictionary with the new entry added."
        )
        error: str = SchemaField(description="Error message if the operation failed.")

    def __init__(self):
        super().__init__(
            id="31d1064e-7446-4693-a7d4-65e5ca1180d1",
            description="Adds a new key-value pair to a dictionary. If no dictionary is provided, a new one is created.",
            categories={BlockCategory.BASIC},
            input_schema=AddToDictionaryBlock.Input,
            output_schema=AddToDictionaryBlock.Output,
            test_input=[
                {
                    "dictionary": {"existing_key": "existing_value"},
                    "key": "new_key",
                    "value": "new_value",
                },
                {"key": "first_key", "value": "first_value"},
                {
                    "dictionary": {"existing_key": "existing_value"},
                    "entries": {"new_key": "new_value", "first_key": "first_value"},
                },
            ],
            test_output=[
                (
                    "updated_dictionary",
                    {"existing_key": "existing_value", "new_key": "new_value"},
                ),
                ("updated_dictionary", {"first_key": "first_value"}),
                (
                    "updated_dictionary",
                    {
                        "existing_key": "existing_value",
                        "new_key": "new_value",
                        "first_key": "first_value",
                    },
                ),
            ],
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        updated_dict = input_data.dictionary.copy()

        if input_data.value is not None and input_data.key:
            updated_dict[input_data.key] = input_data.value

        for key, value in input_data.entries.items():
            updated_dict[key] = value

        yield "updated_dictionary", updated_dict


class AddToListBlock(Block):
    class Input(BlockSchema):
        list: List[Any] = SchemaField(
            default_factory=list,
            advanced=False,
            description="The list to add the entry to. If not provided, a new list will be created.",
        )
        entry: Any = SchemaField(
            description="The entry to add to the list. Can be of any type (string, int, dict, etc.).",
            advanced=False,
            default=None,
        )
        entries: List[Any] = SchemaField(
            default_factory=lambda: list(),
            description="The entries to add to the list. This is the batch version of the `entry` field.",
            advanced=True,
        )
        position: int | None = SchemaField(
            default=None,
            description="The position to insert the new entry. If not provided, the entry will be appended to the end of the list.",
        )

    class Output(BlockSchema):
        updated_list: List[Any] = SchemaField(
            description="The list with the new entry added."
        )
        error: str = SchemaField(description="Error message if the operation failed.")

    def __init__(self):
        super().__init__(
            id="aeb08fc1-2fc1-4141-bc8e-f758f183a822",
            description="Adds a new entry to a list. The entry can be of any type. If no list is provided, a new one is created.",
            categories={BlockCategory.BASIC},
            input_schema=AddToListBlock.Input,
            output_schema=AddToListBlock.Output,
            test_input=[
                {
                    "list": [1, "string", {"existing_key": "existing_value"}],
                    "entry": {"new_key": "new_value"},
                    "position": 1,
                },
                {"entry": "first_entry"},
                {"list": ["a", "b", "c"], "entry": "d"},
                {
                    "entry": "e",
                    "entries": ["f", "g"],
                    "list": ["a", "b"],
                    "position": 1,
                },
            ],
            test_output=[
                (
                    "updated_list",
                    [
                        1,
                        {"new_key": "new_value"},
                        "string",
                        {"existing_key": "existing_value"},
                    ],
                ),
                ("updated_list", ["first_entry"]),
                ("updated_list", ["a", "b", "c", "d"]),
                ("updated_list", ["a", "f", "g", "e", "b"]),
            ],
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        entries_added = input_data.entries.copy()
        if input_data.entry:
            entries_added.append(input_data.entry)

        updated_list = input_data.list.copy()
        if (pos := input_data.position) is not None:
            updated_list = updated_list[:pos] + entries_added + updated_list[pos:]
        else:
            updated_list += entries_added

        yield "updated_list", updated_list


class FindInListBlock(Block):
    class Input(BlockSchema):
        list: List[Any] = SchemaField(description="The list to search in.")
        value: Any = SchemaField(description="The value to search for.")

    class Output(BlockSchema):
        index: int = SchemaField(description="The index of the value in the list.")
        found: bool = SchemaField(
            description="Whether the value was found in the list."
        )
        not_found_value: Any = SchemaField(
            description="The value that was not found in the list."
        )

    def __init__(self):
        super().__init__(
            id="5e2c6d0a-1e37-489f-b1d0-8e1812b23333",
            description="Finds the index of the value in the list.",
            categories={BlockCategory.BASIC},
            input_schema=FindInListBlock.Input,
            output_schema=FindInListBlock.Output,
            test_input=[
                {"list": [1, 2, 3, 4, 5], "value": 3},
                {"list": [1, 2, 3, 4, 5], "value": 6},
            ],
            test_output=[
                ("index", 2),
                ("found", True),
                ("found", False),
                ("not_found_value", 6),
            ],
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            yield "index", input_data.list.index(input_data.value)
            yield "found", True
        except ValueError:
            yield "found", False
            yield "not_found_value", input_data.value


class NoteBlock(Block):
    class Input(BlockSchema):
        text: str = SchemaField(description="The text to display in the sticky note.")

    class Output(BlockSchema):
        output: str = SchemaField(description="The text to display in the sticky note.")

    def __init__(self):
        super().__init__(
            id="cc10ff7b-7753-4ff2-9af6-9399b1a7eddc",
            description="This block is used to display a sticky note with the given text.",
            categories={BlockCategory.BASIC},
            input_schema=NoteBlock.Input,
            output_schema=NoteBlock.Output,
            test_input={"text": "Hello, World!"},
            test_output=[
                ("output", "Hello, World!"),
            ],
            block_type=BlockType.NOTE,
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        yield "output", input_data.text


class CreateDictionaryBlock(Block):
    class Input(BlockSchema):
        values: dict[str, Any] = SchemaField(
            description="Key-value pairs to create the dictionary with",
            placeholder="e.g., {'name': 'Alice', 'age': 25}",
        )

    class Output(BlockSchema):
        dictionary: dict[str, Any] = SchemaField(
            description="The created dictionary containing the specified key-value pairs"
        )
        error: str = SchemaField(
            description="Error message if dictionary creation failed"
        )

    def __init__(self):
        super().__init__(
            id="b924ddf4-de4f-4b56-9a85-358930dcbc91",
            description="Creates a dictionary with the specified key-value pairs. Use this when you know all the values you want to add upfront.",
            categories={BlockCategory.DATA},
            input_schema=CreateDictionaryBlock.Input,
            output_schema=CreateDictionaryBlock.Output,
            test_input=[
                {
                    "values": {"name": "Alice", "age": 25, "city": "New York"},
                },
                {
                    "values": {"numbers": [1, 2, 3], "active": True, "score": 95.5},
                },
            ],
            test_output=[
                (
                    "dictionary",
                    {"name": "Alice", "age": 25, "city": "New York"},
                ),
                (
                    "dictionary",
                    {"numbers": [1, 2, 3], "active": True, "score": 95.5},
                ),
            ],
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            # The values are already validated by Pydantic schema
            yield "dictionary", input_data.values
        except Exception as e:
            yield "error", f"Failed to create dictionary: {str(e)}"


class CreateListBlock(Block):
    class Input(BlockSchema):
        values: List[Any] = SchemaField(
            description="A list of values to be combined into a new list.",
            placeholder="e.g., ['Alice', 25, True]",
        )
        max_size: int | None = SchemaField(
            default=None,
            description="Maximum size of the list. If provided, the list will be yielded in chunks of this size.",
            advanced=True,
        )

    class Output(BlockSchema):
        list: List[Any] = SchemaField(
            description="The created list containing the specified values."
        )
        error: str = SchemaField(description="Error message if list creation failed.")

    def __init__(self):
        super().__init__(
            id="a912d5c7-6e00-4542-b2a9-8034136930e4",
            description="Creates a list with the specified values. Use this when you know all the values you want to add upfront.",
            categories={BlockCategory.DATA},
            input_schema=CreateListBlock.Input,
            output_schema=CreateListBlock.Output,
            test_input=[
                {
                    "values": ["Alice", 25, True],
                },
                {
                    "values": [1, 2, 3, "four", {"key": "value"}],
                },
            ],
            test_output=[
                (
                    "list",
                    ["Alice", 25, True],
                ),
                (
                    "list",
                    [1, 2, 3, "four", {"key": "value"}],
                ),
            ],
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            max_size = input_data.max_size or len(input_data.values)
            for i in range(0, len(input_data.values), max_size):
                yield "list", input_data.values[i : i + max_size]
        except Exception as e:
            yield "error", f"Failed to create list: {str(e)}"


class TypeOptions(enum.Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    DICTIONARY = "dictionary"


class UniversalTypeConverterBlock(Block):
    class Input(BlockSchema):
        value: Any = SchemaField(
            description="The value to convert to a universal type."
        )
        type: TypeOptions = SchemaField(description="The type to convert the value to.")

    class Output(BlockSchema):
        value: Any = SchemaField(description="The converted value.")

    def __init__(self):
        super().__init__(
            id="95d1b990-ce13-4d88-9737-ba5c2070c97b",
            description="This block is used to convert a value to a universal type.",
            categories={BlockCategory.BASIC},
            input_schema=UniversalTypeConverterBlock.Input,
            output_schema=UniversalTypeConverterBlock.Output,
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            converted_value = convert(
                input_data.value,
                {
                    TypeOptions.STRING: str,
                    TypeOptions.NUMBER: float,
                    TypeOptions.BOOLEAN: bool,
                    TypeOptions.LIST: list,
                    TypeOptions.DICTIONARY: dict,
                }[input_data.type],
            )
            yield "value", converted_value
        except Exception as e:
            yield "error", f"Failed to convert value: {str(e)}"
