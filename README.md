# Lsetwatch CSV import/export

A Python implementation of the Lsetwatch CSV export/import format.

[Lsetwatch](https://lebostein.de/lsetwatch/index.html) is an offline LEGO collection management software.

## Data format

The data format and fields are partially described in the [Lsetwatch documentation](https://lebostein.de/lsetwatch/faq_de.html#IEM).

### CSV dialect

The CSV specification used by Lsetwatch is implemented with a custom [CSV dialect](https://docs.python.org/3/library/csv.html#dialects-and-formatting-parameters):

* Lsetwatch is using semicolon-separated values; and the line terminator `\r\n`; without quoting of values. This is implemented in`LsetWatchDialect`.

### Value encoding

Values are escaped within the application itself. The value encoding used by Lsetwatch is implemented with custom [stateless Codecs](https://docs.python.org/3/library/codecs.html#codec-base-classes):

* The Bell character `\a` is used for escaping reserved CSV characters. This is implemented in `BellEscapedAsciiStringCodec`.
* Lists are represented as pipe-separated values within a field. This is implemented in `PipeSeparatedListCodec`. Note that as of Lsetwatch 1.17 values within lists don't seem to be escaped correctly, and can cause invalid outputs (e.g. using the pipe character `|` within values in lists).

### Locales, date and number format

The date and decimal number formats are configurable within Lsetwatch. This is also
the case in this library and the formats needs to match the values configured within
Lsetwatch when parsing or generating CSV output.

If no formats are specified, the following defaults are used:

* Dates: `dd/MM/yyyy`.
* Decimal numbers: Comma as thousands separator, and period as decimal separator.