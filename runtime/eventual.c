#ifdef _WIN32
#include <Windows.h>
struct loop {
    HANDLE iocp;
};

int et_init(void* loop_)
{
    struct loop* loop = (struct loop*)loop_;
    loop->iocp = CreateIoCompletionPort(
        INVALID_HANDLE_VALUE, NULL, 0, 0); 
    return 0;
}

int et_notify(void* loop_)
{
    struct loop* loop = (struct loop*)loop_;
    PostQueuedCompletionStatus(loop->iocp, 0, 0, NULL);
    return 0;
}

int et_wait(void* loop_, long timeout)
{
    struct loop* loop = (struct loop*)loop_;
    OVERLAPPED *ovl;
    ULONG_PTR completionkey;
    DWORD transferred;
    DWORD milliseconds = (timeout == -1)?INFINITE:timeout;
    GetQueuedCompletionStatus(loop->iocp,
        &transferred, &completionkey, &ovl, milliseconds);
    return 0;
}


#else
#include <stdint.h>
#include <stdio.h>
#include <sys/eventfd.h>
#include <sys/select.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>

struct loop {
    int eventfd;
};

int et_init(void* loop_)
{
    struct loop* loop = (struct loop*)loop_;
    loop->eventfd = eventfd(0, 0);
    return 0;
}

int et_notify(void* loop_)
{
    struct loop* loop = (struct loop*)loop_;
    uint64_t buf = 1;
    write(loop->eventfd, &buf, sizeof(uint64_t));
    return 0;
}

int et_wait(void* loop_, long timeout)
{
    struct loop* loop = (struct loop*)loop_;

    struct timeval timeval = {0, 0};
    struct timeval* timeval_p = &timeval;
    if (timeout == -1) {
        timeval_p = NULL;
    } else {
        timeval.tv_usec = timeout * 1000;
    }

    fd_set read_fd_set;
    FD_ZERO(&read_fd_set);
    FD_SET(loop->eventfd, &read_fd_set);
    select (FD_SETSIZE, &read_fd_set, NULL, NULL, timeval_p);

    if (FD_ISSET(loop->eventfd, &read_fd_set)) {
        uint64_t count;
        read(loop->eventfd, &count, sizeof(uint64_t));
    }
    // We ignore whole lot of things here again.

    return 0;
}
#endif

// This one is generic.
size_t et_sizeof(int which)
{
    switch (which) {
        case 0:
            return sizeof(struct loop);
    }
    return 0;
}
