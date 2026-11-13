#pragma once
// Platform process-lifetime/I/O glue only; numerical and framing code is unchanged.
#include <csignal>
#include <stdexcept>
#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <tlhelp32.h>
#include <fcntl.h>
#include <io.h>
#include <thread>
inline void protect_parent() {
    if (_setmode(_fileno(stdin), _O_BINARY)<0 || _setmode(_fileno(stdout), _O_BINARY)<0)
        throw std::runtime_error("binary framed I/O setup failed");
    DWORD parent=0;
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
    if(snapshot==INVALID_HANDLE_VALUE)throw std::runtime_error("parent snapshot failed");
    PROCESSENTRY32 entry{};entry.dwSize=sizeof(entry);
    if(Process32First(snapshot,&entry))do {
        if(entry.th32ProcessID==GetCurrentProcessId()){parent=entry.th32ParentProcessID;break;}
    } while(Process32Next(snapshot,&entry));
    CloseHandle(snapshot);
    HANDLE handle=OpenProcess(SYNCHRONIZE|PROCESS_QUERY_LIMITED_INFORMATION,FALSE,parent);
    FILETIME pc{},pe{},pk{},pu{},cc{},ce{},ck{},cu{};
    if(!parent || !handle || !GetProcessTimes(handle,&pc,&pe,&pk,&pu)
       || !GetProcessTimes(GetCurrentProcess(),&cc,&ce,&ck,&cu)
       || CompareFileTime(&pc,&cc)>0 || WaitForSingleObject(handle,0)!=WAIT_TIMEOUT) {
        if(handle)CloseHandle(handle);
        throw std::runtime_error("engine parent-lifetime guard failed");
    }
    std::thread([handle](){WaitForSingleObject(handle,INFINITE);CloseHandle(handle);
        TerminateProcess(GetCurrentProcess(),127);}).detach();
}
#elif defined(__linux__)
#include <sys/prctl.h>
#include <unistd.h>
inline void protect_parent() {
    const auto parent=getppid();
    if(parent<=1||prctl(PR_SET_PDEATHSIG,SIGKILL)!=0||getppid()!=parent)
        throw std::runtime_error("engine parent-lifetime guard failed");
}
#elif defined(__APPLE__)
#include <unistd.h>
#include <chrono>
#include <thread>
inline void protect_parent() {
    const auto parent=getppid();
    if(parent<=1)throw std::runtime_error("engine parent-lifetime guard failed");
    std::thread([parent](){for(;;){
        if(getppid()!=parent){kill(getpid(),SIGKILL);return;}
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }}).detach();
    if(getppid()!=parent)throw std::runtime_error("engine parent-lifetime guard failed");
}
#else
#error Unsupported native client platform
#endif
