#!/usr/bin/perl

# Sleep to allow Tomcat to create catalina.out
sleep 1;

$SERVER = $ARGV[0];

open IF, "tail -f /home/ajclisso/uportal/tomcat/logs/catalina.out|";

$ready = 0;
while (!($ready)) {
        $line = <IF>;
        if ($line =~ /Server startup/) {
                $ready = 1;
        }
}                         
