#pragma once
#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <tlhelp32.h>
#include <stdexcept>
#include <thread>
// Retain a handle to the exact parent, including a creation-time check against
// PID reuse. A killed Python driver must not leave an unowned GPU process.
inline void protect_parent() {
    DWORD parent=0;
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
    if(snapshot==INVALID_HANDLE_VALUE) throw std::runtime_error("Parent snapshot failed");
    PROCESSENTRY32 entry{};entry.dwSize=sizeof(entry);
    if(Process32First(snapshot,&entry)) do {
        if(entry.th32ProcessID==GetCurrentProcessId()){parent=entry.th32ParentProcessID;break;}
    } while(Process32Next(snapshot,&entry));
    CloseHandle(snapshot);
    HANDLE handle=OpenProcess(SYNCHRONIZE|PROCESS_QUERY_LIMITED_INFORMATION,FALSE,parent);
    FILETIME pc{},pe{},pk{},pu{},cc{},ce{},ck{},cu{};
    if(!parent || !handle || !GetProcessTimes(handle,&pc,&pe,&pk,&pu)
       || !GetProcessTimes(GetCurrentProcess(),&cc,&ce,&ck,&cu)
       || CompareFileTime(&pc,&cc)>0 || WaitForSingleObject(handle,0)!=WAIT_TIMEOUT) {
        if(handle) CloseHandle(handle);
        throw std::runtime_error("Parent-lifetime guard failed");
    }
    std::thread([handle](){WaitForSingleObject(handle,INFINITE);CloseHandle(handle);
        TerminateProcess(GetCurrentProcess(),127);}).detach();
}
#else
inline void protect_parent() {} // Linux additionally uses PR_SET_PDEATHSIG in Python.
#endif
