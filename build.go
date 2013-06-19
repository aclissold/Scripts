package main

import (
    "fmt"
    "strings"
    "path/filepath"
    "os"
    "io"
    "log"
    "flag"
    "runtime"
    "time"
    "github.com/bpowell/golib/multilog"
    "github.com/bpowell/golib/cmdexec"
)

func main() {

    start := time.Now()

    portlets := map[string] string {
        "courses/courses-portlet-webapp": "CoursesPortlet.war",
        "announcements": "Announcements.war",
        "feedback": "FeedbackPortlet.war",
        "finaid": "finaid.war",
        "map": "MapPortlet.war",
        "mydetails": "mydetails.war",
        "password": "password.war",
        "tester": "uPortalTester.war",
        "progress": "CourseSchedulePortlet.war",
        "courses": "CoursesPortlet.war",
        "calendar": "CalendarPortlet.war",
    }

    // set up flags
    ENV := flag.String("env", "local", "Set environment.")
    UPDATE := flag.Bool("update", false, "Determine whether to run updates or not.")
    BUILD_ANT_TARGET := flag.String("build.ant.target", "clean deploy-ear", "Set the ant build target.")
    BUILD_PORTAL := flag.Bool("build.portal", false, "Determine whether to build uPortal or not.")
    BUILD_PORTLETS := flag.Bool("build.portlets", false, "Determine whether to build portlets or not.")
    MVNC := flag.Bool("maven.tests", false, "Run maven tests.")
    flag.Parse()

    // uportal cwd
    UPORTAL, err := os.Getwd()
    if err != nil {
        fmt.Println("Could not get current working directory.")
        fmt.Println(err)
        os.Exit(2)
    }
    fmt.Println("uPortal directory is set to:",UPORTAL)

    // env
    fmt.Println("Building for environment:",*ENV)

    // program[0] = tomcat
    // program[1] = mvn
    // program[2]=ant
    // program[3] = groovy
    programs := check_for_programs()

    c := make(chan string)
    if *UPDATE {
        run_updates()
    }

    // channel counter
    n := 0

    if *BUILD_PORTLETS {
        for portlet, war := range portlets {
            n++
            go build_portlet(programs, *ENV, portlet, war, UPORTAL, *MVNC, c)
        }
        for i := 0; i < n; i++ {
            fmt.Print(<-c)
            fmt.Printf("\n%.2fs total\n", time.Since(start).Seconds())
        }
    }

    if *BUILD_PORTAL {
        build_portal(programs["ant"], *ENV, *BUILD_ANT_TARGET)
    }
}

func build_portlet(programs map[string] string, ENV string, portlet string, war string, UPORTAL string, mvnc bool, c chan<- string) {
    fmt.Println("Deploying:",portlet)
    work, _ := exists("work")
    if !work {
        os.Mkdir("work", 0755)
    }
    workexists, _ := exists("work/"+portlet)
    if !workexists {
        os.Mkdir("work/"+portlet, 0755)
    }
    // jasig
    fmt.Println("Copying jasig/"+portlet+" to work/"+portlet)
    err := CopyDir("jasig/", "work/", portlet, UPORTAL)
    if err != nil {
        log.Fatal(err)
    } else {
        log.Print("Jasig folder copied for: "+portlet)
    }
    // overlay
    overlayexists, _ := exists("overlay/"+portlet)
    if overlayexists {
        fmt.Println("Copying overlay/"+portlet+" to work/"+portlet)
        err := CopyDir("overlay/", "work/", portlet, UPORTAL)
        if err != nil {
            log.Fatal(err)
        } else {
            log.Print("Overlay copied for: "+portlet)
        }
    }

    mvncommand := "clean package"
    if portlet == "courses/courses-portlet-webapp" {
        mvncommand = "clean install"
    }
    if mvnc {
        mvncommand += " -Dmaven.tests.skip=false"
    }
    // mvn clean package/install
    fmt.Println("Now running "+programs["mvn"]+" -f work/"+portlet+"/pom.xml -Denv="+ENV+" -Dfilters.file="+UPORTAL+"/filters/"+ENV+".properties "+mvncommand)
    c <- run_cmd(programs["mvn"], "-f work/"+portlet+"/pom.xml -Denv="+ENV+" -Dfilters.file="+UPORTAL+"/filters/"+ENV+".properties "+mvncommand)
    time.Sleep(1e2)
    if portlet != "courses" {
        // ant deployPortletApp
        fmt.Println("Now running "+programs["ant"]+" -Denv="+ENV+" deployPortletApp -DportletApp=work/"+portlet+"/target/"+war)
        c <- run_cmd(programs["ant"], "-Denv="+ENV+" deployPortletApp -DportletApp=work/"+portlet+"/target/"+war)
        time.Sleep(1e2)
    } else {
        c <- fmt.Sprint(portlet+" built successfully.")
    }
}

func exists(path string) (bool, error) {
    _, err := os.Stat(path)
    if err == nil {
        fmt.Println(path+" exists.")
        return true, nil
    }
    if os.IsNotExist(err) {
        fmt.Println(path+" does not exist.")
        //os.Exit(3)
        return false, nil
    }
    return false, err
}

func build_portal(ant string, ENV string, ant_target string) {
    fmt.Println("Building & deploying uPortal.")
    fmt.Println("Calling on uPortal's build & deploy process.")
    run_cmd(ant,"-Denv="+ENV+" "+ant_target)
}

func check_for_programs() map[string] string {
    tomcat := os.Getenv("TOMCAT_HOME")
    mvn := os.Getenv("M2_HOME")
    ant := os.Getenv("ANT_HOME")
    groovy := os.Getenv("GROOVY_HOME")
    if len(tomcat) > 0 && len(mvn) > 0 && len(ant) > 0 && len(groovy) > 0 {
        programs := map[string] string {
            "mvn": mvn+"/bin/",
            "ant": ant+"/bin/",
            "groovy": groovy+"/bin/",
        }
        switch runtime.GOOS {
            case "windows": for name, exe := range programs {
                programs[name] = exe+name+".bat"
                fmt.Println("Using: "+programs[name])
            }
            case "linux": for name, exe := range programs {
                programs[name] = exe+name
                fmt.Println("Using: "+programs[name])
            }
        }
        return programs
    } else {
        fmt.Println("Missing build requirements. Check that $TOMCAT_HOME, $M2_HOME, $ANT_HOME and $GROOVY_HOME environmental variables are set.")
        //os.Exit(2)
        return nil
    }
}

func run_updates() {
    cmds := map[string] string {
        "git": "pull",
        "groovy": "update.groovy",
    }
    for cmd, arg := range cmds {
        run_cmd(cmd, arg)
    }
}

func run_cmd(prgm string, arg string) string {
    a, _ := multilog.NewMultiLog(prgm+" "+arg, 6, "build.log")
    cmd := cmdexec.NewCmdExec(a)
    cmd.Exec(prgm+" "+arg)
    return prgm+" "+arg+" ran successfully."
}

func CopyDir(src string, prefix string, portlet string, root string) error {
    err := filepath.Walk(src+portlet, func(path string, info os.FileInfo, e error) error {
        exist, _ := exists(strings.Replace(path, src, prefix, 1))
        if !exist {
            switch mode := info.Mode(); {
                case mode.IsDir():
                    os.MkdirAll(strings.Replace(path, src, prefix, 1), 0755)
                    //fmt.Println("Making directory: "+strings.Replace(path, src, prefix, 1))
                case mode.IsRegular():
                    os.Create(strings.Replace(path, src, prefix, 1))
                    //fmt.Println("path: "+path)
                    //fmt.Println("to: "+strings.Replace(path, src, prefix, 1))
                    CopyFile(path, strings.Replace(path, src, prefix, 1))
            }
        } else {
            if len(path) > 0 {
                CopyFile(path, strings.Replace(path, src, prefix, 1))
            }
        }
        return e
    })
    return err
}

func CopyFile(src string, dest string) (int64, error) {
    sf, err := os.Open(src)
    if err != nil {
        return 0, err
    }
    defer sf.Close()
    df, err := os.Create(dest)
    if err != nil {
        return 0, err
    }
    defer df.Close()
    return io.Copy(df, sf)
}
