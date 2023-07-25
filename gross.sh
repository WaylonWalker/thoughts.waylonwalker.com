#!/bin/bash

set -m # to make job control work
thoughts api run &
datasette posts.db &
fg %1 # gross!
