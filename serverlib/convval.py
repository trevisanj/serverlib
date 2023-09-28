"""
Plugin-capable conversion and validation of arguments

Based on ancient sacca::convert_and_validate_args.py
20230927 conversion for printing ("powertabulate") moved here for reuse in HTML generation
"""

__all__ = ["convert_values", "update_row", "validate_values", "convert_and_validate",
           "converters", "validators", "insert_row", "normalize_time_of_day", "validate_time_of_day",
           "convert_rows", "powertabulatemap"]

import inspect, a107, pl3, textwrap
import dateutil


def _convert_whenthis(whenthis):
    if whenthis is None:
        return None
    return a107.to_ts_utc(whenthis)


# Update converters and validators at will!

# Conversion:
#
# {columnname: callable, ...}
#
# callable(value) --> new value
converters = {
    "time_of_day": lambda x: normalize_time_of_day(x),
}

# Validation
#
# {columnname: callable, ...}
#
# callable(value) --> (A): return None (validation passed)
#                     (B.A): raise
#                     (B.B): return str (error message)
#                            Advantage of (B.B) is that errors can be collected and raised at once
#                            with single ValueError
validators = {
    "time_of_day": lambda x: validate_time_of_day(x),
}


async def convert_and_validate(cols_values):
    convert_values(cols_values)
    await validate_values(cols_values)


def convert_values(cols_values):
    for columnname, value in cols_values.items():
        converter = converters.get(columnname)
        if converter:
            cols_values[columnname] = converter(value)
        else:
            if columnname.startswith("flag"): converter = a107.to_bool
            elif "whenthis" in columnname: converter = _convert_whenthis
            else: converter = converters.get(columnname)

            if converter:
                cols_values[columnname] = converter(value)


async def validate_values(cols_values):
    async def apply(validator, value):
        if inspect.iscoroutinefunction(validator):
            return await validator(value)
        else:
            return validator(value)

    errors = []
    for columnname, value in cols_values.items():
        validator = validators.get(columnname)
        if validator:
            result = await apply(validator, value)
            if isinstance(result, str):
                errors.append(result)
        else:
            validator = validators.get(columnname)
            if validator:
                result = await apply(validator, value)
                if isinstance(result, str):
                    errors.append(result)

    if errors:
        raise ValueError("\n".join(errors))


async def update_row(db, tablename, id_, cols_values, columnnames=None):
    """Updates single table row using pairs columnname=value

    Args:
        db: a107.FileSQLite
        tablename:
        id_: row id within table (fieldname must be "id")
        cols_values: list or dict. If list, must come in pairs [columnname0, value0, columnname1, value1, ...]; if dict,
                     {columnname0: value0, columnname1: value1, ...}
        columnnames: list of column names that may be accepted. If not specified, will query the database for the
                     columns of table and accept any column name except "id"
    """

    # Gets columnnames
    if columnnames is None:
        columnnames = [row["name"] for row in db.describe(tablename) if row["name"] != "id"]

    # Converts cols_values to dict
    if isinstance(cols_values, (list, tuple)):
        cols_values = _convert_to_dict(cols_values)

    # Probes existence of id_ in table
    rows = db.execute(f"select id from {tablename} where id=?", (id_,)).fetchall()
    if not rows:
        raise a107.NoData(f"Invalid id for table '{tablename}': {id_}")

    # Conversion
    convert_values(cols_values)

    # Validation
    for columnname, value in cols_values.items():
        if columnname not in columnnames:
            raise ValueError(f"Invalid column: '{columnname}' (valid column names are {columnnames})")
    await validate_values(cols_values)

    bindings = list(cols_values.values())+[id_]
    equals = ", ".join([f"{columnname}=?" for columnname in cols_values])
    sqlito = f"update {tablename} set {equals} where id=?"
    db.execute(sqlito, bindings)


async def insert_row(db, tablename, cols_values, columnnames=None):
    """Updates single table row using pairs columnname=value

    Args:
        db: a107.FileSQLite
        tablename:
        cols_values: list or dict. If list, must come in pairs [columnname0, value0, columnname1, value1, ...]; if dict,
                     {columnname0: value0, columnname1: value1, ...}
        columnnames: list of column names that may be accepted. If not specified, will query the database for the
                     columns of table and accept any column name except "id"
    """

    # Gets columnnames
    if columnnames is None:
        columnnames = [row["name"] for row in db.describe(tablename) if row["name"] != "id"]

    # Converts cols_values to dict
    if isinstance(cols_values, (list, tuple)):
        cols_values = _convert_to_dict(cols_values)

    # Conversion
    convert_values(cols_values)

    # Validation
    for columnname, value in cols_values.items():
        if columnname not in columnnames:
            raise ValueError(f"Invalid column: '{columnname}' (valid column names are {columnnames})")
    await validate_values(cols_values)

    colnames, bindings = zip(*((k, v) for k, v in cols_values.items()))
    sqlito = f"insert into {tablename} ({','.join(colnames)}) values ({','.join(['?']*len(bindings))})"
    db.execute(sqlito, bindings)


def _convert_to_dict(cols_values):
    ncols = len(cols_values)/2
    if ncols < 1 or int(ncols) != ncols:
        raise ValueError("cols_values must come in pairs")
    cols_values = {name: value for name, value in zip(cols_values[0::2], cols_values[1::2])}
    return cols_values


def normalize_time_of_day(s):
    """Normalizes"""
    if s is None:
        return s
    s = s.strip()
    if s:
        return dateutil.parser.parse(s).strftime("%H:%M:%S")
    return ""


def validate_time_of_day(s):
    if s is None:
        return True
    s = s.strip()
    try:
        if s:
            dateutil.parser.parse(s)
    except ValueError:
        return False
    return True


# ======================================================================================================================
# POWERTABULATE part


powertabulatemap = [
    {"fieldnames": ("whenthis", "startts", "ts", "ts0", "ts1", "lasttime", "nexttime", "whenthisenter", "whenthisexit"),
     "converter": lambda x: a107.dt2str(a107.to_datetime(x)), },
    # "converter": lambda x: a107.ts2str(x, tz=a107.utc)},
    {"fieldnames": ("period",),
     "converter": pl3.QP.to_str},
    {"fieldnames": ("error", "lasterror",),
     "converter": lambda x: "\n".join(textwrap.wrap(x, 50))},
    {"fieldnames": ("narration", "memo"),
     "converter": lambda x: "\n".join(textwrap.wrap(x, 50))},
    {"fieldnames": ("hash",),
     "converter": lambda x: "\n".join(textwrap.wrap(x, 40))},
    {"fieldnames": ("flag",),
     "converter": lambda x: str(x)}
]


def convert_rows(rows, header, logger):
    mymap = [[[i for i, h in enumerate(header)
               if any(h.startswith(prefix) for prefix in row["fieldnames"])], row["converter"]] for row in
             powertabulatemap]
    mymap = [x for x in mymap if x[0]]
    if mymap:
        for row in rows:
            for indexes, converter in mymap:
                for i in indexes:
                    try:
                        if row[i] is not None:
                            row[i] = converter(row[i])
                    except BaseException as e:
                        logger.error(f"Error '{a107.str_exc(e)}' while trying to apply convertion to field "
                                       f"'{header[i]}' with value {repr(row[i])}")
                        raise
