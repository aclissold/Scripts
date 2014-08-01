#!/bin/bash
#
# Steve Wiggins's Tomcat start/stop command

tomcat="org\.apache.*Bootstrap"

for i in "$@"; do
    if [[ $i == "start" ]]; then
        if [[ -n `ps aux | grep $tomcat` ]]; then
            echo Error: Tomcat is already running.
        else
            $TOMCAT_HOME/bin/startup.sh
            sleep 5
            psiman -s
        fi
    elif [[ $i == "stop" ]]; then
        kill -9 $(ps aux | grep $tomcat | awk '{print $2}')
        sleep 5
    elif [[ $i == "restart" ]]; then
        $0 stop
        $0 start
    elif [[ $i == "clean" ]]; then
        rm -rf $TOMCAT_HOME/webapps/*
        rm -rf $TOMCAT_HOME/work/Catalina/localhost/*
    elif [[ $i == "s" || $i == "status" ]]; then
        ps aux | grep $tomcat
    else
        echo "whachu tryna do"
    fi
done
