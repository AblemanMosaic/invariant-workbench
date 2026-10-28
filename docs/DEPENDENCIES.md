# Dependencies and version sovereignty

Core proof, BDD, pure lifecycle, adapters-as-data, static reports and Mosaic HEADLESS
use the Python standard library plus bundled, exact pinned source. Full acceptance
also invokes native UCM fixture signature code, which requires `cryptography`, and
validates the realization-space examples against Draft 2020-12 with `jsonschema`.
Builder-observed versions belong in host evidence; no package is installed implicitly
and the user may retain a working pinned environment.

Optional live database work requires psycopg 3 and PostgreSQL. Their actual versions
were not exercised by this builder, so no verified version tuple is invented.
Pin the locally chosen versions and retain the live harness outputs. The code uses
psycopg3 `connect`, `execute`, `commit`, `rollback` and transaction SQL.

The actual Mosaic Windows runtime uses native Win32 controls via ctypes. The Linux
builder can validate HEADLESS and fake-host control binding, not native HWND behavior.
The optional model client uses the documented Ollama `/api/chat` shape with stream=false
and format=json; actual model execution is NOT_RUN. A loopback endpoint is not proof
of the model server's offline behavior.

The C++ differential probe uses g++ with undefined-behavior sanitization in the builder
campaign. It does not establish Zucchini or C++ formal correctness. The upstream build
harness requires an explicitly reviewed source export and preinstalled dependencies.

References consulted, not substituted for live observations:
https://docs.ollama.com/api/chat
https://www.psycopg.org/psycopg3/docs/basic/transactions.html
https://www.postgresql.org/docs/current/transaction-iso.html
https://raw.githubusercontent.com/AnarchoSystems/Zucchini/main/CMakeLists.txt
