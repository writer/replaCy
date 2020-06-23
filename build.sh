#!/bin/bash
set -e

SERVICE_NAME="replacy"
BASE_STRING=$(cat VERSION)
BASE_LIST=($(echo "$BASE_STRING" | tr '.' ' '))
V_MAJOR=${BASE_LIST[0]}
V_MINOR=${BASE_LIST[1]}
V_PATCH=${BASE_LIST[2]}
echo -e "Current version: $BASE_STRING"
V_MINOR=$((V_MINOR + 1))
V_PATCH=0
SUGGESTED_VERSION="$V_MAJOR.$V_MINOR.$V_PATCH"


update_deps ()
{
    echo "quitely installing dependencies..."
    python3 -m pip install -q --upgrade twine
    python3 -m pip install -q setuptools wheel
    python3 -m pip install -qr requirements.txt
    python3 -m pip install -qr requirements-dev.txt
}

run_tests()
{
    python3 test.py
}

bump_version ()
{
    echo "Bumping minor version in VERSION file"
    echo ""
    echo "$SUGGESTED_VERSION" > VERSION
}


create_dist ()
{
    echo "generating source distribution - this step bumps version.py to match VERSION"
    echo ""
    python3 setup.py sdist
}


#########################
# Actually run the code #
#########################

update_deps
run_tests
bump_version
create_dist
