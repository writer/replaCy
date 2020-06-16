#!/bin/bash
set -e

SERVICE_NAME="replacy"
NOW="$(date +'%B %d, %Y')"
BASE_STRING=$(cat VERSION)
BASE_LIST=($(echo "$BASE_STRING" | tr '.' ' '))
V_MAJOR=${BASE_LIST[0]}
V_MINOR=${BASE_LIST[1]}
V_PATCH=${BASE_LIST[2]}
echo -e "Current version: $BASE_STRING"
V_MINOR=$((V_MINOR + 1))
V_PATCH=0
SUGGESTED_VERSION="$V_MAJOR.$V_MINOR.$V_PATCH"

INVENV=$(python3 -c 'import sys; print ("1" if hasattr(sys, "base_prefix") else "0")')
CREDS_LOCATION=$1


check_credential_file_exists ()
{
    if [ ! -z "${CREDS_LOCATION_ENV}" ]; then
        echo "credentials were passed in environment"
        CREDS_LOCATION=${CREDS_LOCATION_ENV}
        PYPIRC="creds"
    elif [ ! -z "${CREDS_LOCATION}" ]; then
        echo "credentials were passed in as argument"
        PYPIRC="creds"
    elif [ -f .pypirc ]; then
        echo "found .pypirc in project directory..."
        PYPIRC="here"
    elif [ -f ~/.pypirc ]; then
        echo "found .pypirc in user home directory..."
        PYPIRC="root"
    else
        echo "## MISSING .pypirc file, can't release to PyPi!"
        exit 1
    fi
}

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

upload_to_pypi ()
{
    echo "uploading to Pypi"
    if [ $PYPIRC = "here" ]; then
        python3 -m twine upload -r pypi --config-file .pypirc dist/"$SERVICE_NAME"-"$SUGGESTED_VERSION".tar.gz
    elif [ $PYPIRC = "creds" ]; then
        python3 -m twine upload -r pypi --config-file "$CREDS_LOCATION" dist/"$SERVICE_NAME"-"$SUGGESTED_VERSION".tar.gz
    else
        python3 -m twine upload -r pypi --config-file ~/.pypirc dist/"$SERVICE_NAME"-"$SUGGESTED_VERSION".tar.gz
    fi
}


#########################
# Actually run the code #
#########################

#check_credential_file_exists
update_deps
run_tests
bump_version
create_dist
#upload_to_pypi
