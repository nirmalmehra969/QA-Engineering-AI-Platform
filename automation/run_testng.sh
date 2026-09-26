#!/usr/bin/env bash
echo "==================================================="
echo " Launching Java + Selenium + TestNG Automation Run"
echo "==================================================="
cd "$(dirname "$0")"
mvn clean test -DbaseUrl=http://127.0.0.1:5000/app/target-store
