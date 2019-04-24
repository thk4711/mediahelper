#!/bin/bash
while :
do
  cat /tmp/shairport-sync-metadata | ./shairport-metadata.py
  sleep 1
done
