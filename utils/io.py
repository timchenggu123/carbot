import os
import asyncio
import threading
import queue
import abc

class AsyncFrameFIFO:
    def __init__(self, io_name: str, max_queue_size: int = 10):
        self.io_name = io_name
        self.file_path = f"/tmp/{self.io_name}_carbot_frame_fifo"
        self.read_task = None
        self.write_fd = None
        # Use threading-safe queue instead of asyncio.Queue
        self.frame_queue = queue.Queue(maxsize=max_queue_size)

    async def _read_frames(self):
        """Asynchronously read frames from FIFO and put them into the queue. Removes old frames if the queue is full."""
        print("Read frame called")
        read_fd = os.open(self.file_path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            while True:
                try:
                    # Read larger chunks for JPEG frames (can be 100KB+)
                    frame = os.read(read_fd, 256 * 1024)  # Read up to 256KB
                    # print("Tried to read frame from FIFO")
                    if frame:
                        # print(f"Read frame from FIFO: {len(frame)} bytes")
                        # Use threading-safe queue - remove old frame if full
                        if self.frame_queue.full():
                            try:
                                self.frame_queue.get_nowait()  # Remove oldest frame
                            except queue.Empty:
                                pass
                        self.frame_queue.put_nowait(frame)
                        # print("Added frame to queue")
                    else:
                        await asyncio.sleep(0.01)  # No data, wait a bit
                except BlockingIOError:
                    await asyncio.sleep(0.01)  # No data available, wait a bit
                except Exception as e:
                    # print(f"Error reading from FIFO: {e}")
                    break
        finally:
            os.close(read_fd)

    async def write_frame(self, frame: bytes):
        """Asynchronously write a frame to the FIFO."""
        # print(f"{os.path.exists(self.file_path)=}, {self.write_fd=}")
        if os.path.exists(self.file_path) and self.write_fd is None:
            self.write_fd = os.open(self.file_path, os.O_WRONLY | os.O_NONBLOCK)
            # print("Opened write FD for FIFO")
        if self.write_fd is None:
            # print("Write FD is None, cannot write frame")
            return None
        try:
            os.write(self.write_fd, frame)
            # print(f"Wrote frame to FIFO: {len(frame)} bytes")
        except BlockingIOError:
            # print("BlockIO")
            pass  # Write would block, skip this frame
        except Exception as e:
            print(f"Error writing to FIFO: {e}")
            return None

    def get_frame(self, timeout: float = 1.0):
        """Get a frame from the queue with a timeout."""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def start_reading(self):
        """Start the asynchronous frame reading task."""
        print("Starting frame FIFO reading")
        if not os.path.exists(self.file_path):
            os.mkfifo(self.file_path)
            print("Created FIFO at", self.file_path)
        
        # Run the async function in a separate thread
        def run_async():
            asyncio.run(self._read_frames())
        
        if self.read_task is None:
            self.read_task = threading.Thread(target=run_async, daemon=True)
            self.read_task.start()
            print("Started reading thread")

    def close(self):
        """Close the FIFO and cleanup."""
        if self.read_task is not None:
            # For threading.Thread, we can't cancel, just let it finish
            pass
        if self.write_fd is not None:
            os.close(self.write_fd)
        try:
            os.remove(self.file_path)
        except OSError:
            pass


class AsyncTextFIFO:

    def __init__(self, io_name: str, max_queue_size: int = 50):
        self.io_name = io_name
        self.file_path = f"/tmp/{self.io_name}_carbot_text_fifo"
        self.read_task = None
        self.write_fd = None
        # Use threading-safe queue instead of asyncio.Queue
        self.text_queue = queue.Queue(maxsize=max_queue_size)

    async def _read_lines(self):
        """Asynchronously read lines from FIFO and put them into the queue. Removes old lines if the queue is full."""
        print("Read text lines called")
        read_fd = os.open(self.file_path, os.O_RDONLY | os.O_NONBLOCK)
        buffer = b""
        try:
            while True:
                try:
                    data = os.read(read_fd, 1024)  # Read up to 1KB
                    if data:
                        buffer += data
                        while b'\n' in buffer:
                            line, buffer = buffer.split(b'\n', 1)
                            line_str = line.decode('utf-8')
                            # Use threading-safe queue - remove old line if full
                            if self.text_queue.full():
                                try:
                                    self.text_queue.get_nowait()  # Remove oldest line
                                except queue.Empty:
                                    pass
                            self.text_queue.put_nowait(line_str)
                    else:
                        await asyncio.sleep(0.01)  # No data, wait a bit
                except BlockingIOError:
                    await asyncio.sleep(0.01)  # No data available, wait a bit
                except Exception as e:
                    print(f"Error reading from text FIFO: {e}")
                    break
        finally:
            os.close(read_fd)

    async def write_line(self, line: str):
        """Asynchronously write a line to the FIFO."""
        if os.path.exists(self.file_path) and self.write_fd is None:
            self.write_fd = os.open(self.file_path, os.O_WRONLY | os.O_NONBLOCK)
        if self.write_fd is None:
            return None
        try:
            os.write(self.write_fd, (line + '\n').encode('utf-8'))
        except BlockingIOError:
            pass  # Write would block, skip this line
        except Exception as e:
            print(f"Error writing to text FIFO: {e}")
            return None
        return None

    def write_line_sync(self, line: str):
        """Synchronous wrapper to write a line to the FIFO."""
        asyncio.run(self.write_line(line))

    def readline(self, timeout: float = 1.0):
        """Get a line from the queue with a timeout."""
        try:
            return self.text_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def start_reading(self):
        """Start the asynchronous line reading task."""
        print("Starting text FIFO reading")
        if not os.path.exists(self.file_path):
            os.mkfifo(self.file_path)
            print("Created FIFO at", self.file_path)
        
        # Run the async function in a separate thread
        def run_async():
            asyncio.run(self._read_lines())
        
        if self.read_task is None:
            self.read_task = threading.Thread(target=run_async, daemon=True)
            self.read_task.start()
            print("Started text reading thread")

    def close(self):
        """Close the FIFO and cleanup."""
        if self.read_task is not None:
            # For threading.Thread, we can't cancel, just let it finish
            pass
        if self.write_fd is not None:
            os.close(self.write_fd)
        try:
            os.remove(self.file_path)
        except OSError:
            pass
