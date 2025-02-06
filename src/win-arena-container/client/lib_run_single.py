"""Script to run & evaluate agent-loop on a single example from the benchmark."""
import datetime
import json
import logging
import os
import time
import traceback
from trajectory_recorder import TrajectoryRecorder

logger = logging.getLogger("desktopenv.experiment")

# Open the JSON file
with open("./settings.json", "r") as file:
    # Load the JSON data from the file
    data = json.load(file)
time_limit = data["time_limit"]

def run_single_example(agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    agent.reset()
    obs = env.reset(task_config=example)
    done = False
    step_idx = 0

    #env.controller.start_recording()
    start_time = datetime.datetime.now()
    
    # Initialize recorder, which will save the trajectory as a JSON & HTML in {example_result_dir}/traj.(jsonl,html)
    recorder = TrajectoryRecorder(example_result_dir)
    
    # Record initial state
    init_timestamp = start_time.strftime("%Y%m%d@%H%M%S")
    recorder.record_init(obs, example, init_timestamp)
    
    from mm_agents.server_agents.agent import ServerAgent
    if isinstance(agent, ServerAgent):
        logger.info("Agent: Running server agent %s...", agent.agent_name)
        env.controller.run_agent(agent.agent_name, instruction, agent.agent_settings)
        
    else:
        while not done and step_idx < max_steps:
            if obs is None:
                logger.error("Observation is None. Waiting a little to do next step.")
                time.sleep(5)
                step_idx += 1
                continue

            logger.info("Agent: Thinking...")
            response, actions, logs, computer_update_args = agent.predict(
                instruction,
                obs
            )

            # update the computer object, used by navi's action space
            if computer_update_args:
                env.controller.update_computer(**computer_update_args)

            # step environment with agent actions 
            for action in actions:
                # Capture the timestamp before executing the action
                action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
                elapsed_timestamp = f"{datetime.datetime.now() - start_time}"
                logger.info("Step %d: %s", step_idx + 1, action)

                obs, reward, done, info = env.step(action, args.sleep_after_execution)

                logger.info("Reward: %.2f", reward)
                logger.info("Done: %s", done)

                # Record step data
                recorder.record_step(
                    obs, 
                    logs,
                    step_idx,
                    action_timestamp,
                    elapsed_timestamp,
                    action,
                    reward,
                    done,
                    info
                )

                if done:
                    logger.info("The episode is done.")
                    break
            # inc step counter
            step_idx += 1
    
    logger.info("Running evaluator(s)...")
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)

    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(f"{result}\n")
    
    # Record final results
    recorder.record_end(result, start_time)
    # env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))

###### Pika onboard ######
from mm_agents.pika.planner_agent import Agent
def run_single_pika_example(agent: Agent, env, example, max_steps, instruction, args, example_result_dir, scores):
    env.reset()

    # Try to update the resolution
    env.controller.execute_python_command(f"""
import ctypes

class DEVMODE(ctypes.Structure):
    _fields_ = [("dmDeviceName", ctypes.c_wchar * 32), ("dmSpecVersion", ctypes.c_ushort), 
                ("dmDriverVersion", ctypes.c_ushort), ("dmSize", ctypes.c_ushort),
                ("dmDriverExtra", ctypes.c_ushort), ("dmFields", ctypes.c_ulong),
                ("dmPositionX", ctypes.c_long), ("dmPositionY", ctypes.c_long),
                ("dmDisplayOrientation", ctypes.c_ulong), ("dmDisplayFixedOutput", ctypes.c_ulong),
                ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short),
                ("dmYResolution", ctypes.c_short), ("dmTTOption", ctypes.c_short),
                ("dmCollate", ctypes.c_short), ("dmFormName", ctypes.c_wchar * 32),
                ("dmLogPixels", ctypes.c_ushort), ("dmBitsPerPel", ctypes.c_ulong),
                ("dmPelsWidth", ctypes.c_ulong), ("dmPelsHeight", ctypes.c_ulong),
                ("dmDisplayFlags", ctypes.c_ulong), ("dmDisplayFrequency", ctypes.c_ulong),
                ("dmICMMethod", ctypes.c_ulong), ("dmICMIntent", ctypes.c_ulong),
                ("dmMediaType", ctypes.c_ulong), ("dmDitherType", ctypes.c_ulong),
                ("dmReserved1", ctypes.c_ulong), ("dmReserved2", ctypes.c_ulong),
                ("dmPanningWidth", ctypes.c_ulong), ("dmPanningHeight", ctypes.c_ulong)]

dm = DEVMODE()
dm.dmSize = ctypes.sizeof(DEVMODE)
ctypes.windll.user32.EnumDisplaySettingsW(None, 0, ctypes.byref(dm))

dm.dmPelsWidth = {args.screen_width}
dm.dmPelsHeight = {args.screen_height}
result = ctypes.windll.user32.ChangeDisplaySettingsW(ctypes.byref(dm), 0)
if result != 0:
    raise Exception("Failed to change resolution")
""")

    env.controller.execute_python_command("pyautogui.hotkey('win', 'ctrl', 'f4'); time.sleep(1); pyautogui.hotkey('win', 'ctrl', 'd')")
    obs = env.reset(task_config=example)
    step_idx = 0

    #env.controller.start_recording()
    start_time = datetime.datetime.now()
    
    # TODO: Fix Recorder for Pika which will save the trajectory as a JSON & HTML in {example_result_dir}/traj.(jsonl,html)
    # # Initialize recorder, which will save the trajectory as a JSON & HTML in {example_result_dir}/traj.(jsonl,html)
    # recorder = TrajectoryRecorder(example_result_dir)
    
    # # Record initial state
    # init_timestamp = start_time.strftime("%Y%m%d@%H%M%S")
    # recorder.record_init(obs, example, init_timestamp)

    logger.info(f"Agent: Starting to execute the instruction '{instruction}'")
    # A3: wait for 30 seconds for startup
    time.sleep(30)

    debug_path = os.path.join(example_result_dir, "debug")
    agent.chat(message=instruction, debug_path=debug_path)

    logger.info("Agent: Finished executing the instruction")

    logger.info("Running evaluator(s)...")
    result = env.evaluate()
    logger.info("Result: %.2f", result)
    scores.append(result)

    # Ensure that there is no error.txt file in the debug directory
    if not os.path.exists(os.path.join(debug_path, "error.txt")):
        with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
            f.write(f"{result}\n")

    with open(os.path.join(example_result_dir, "time_taken.txt"), "w", encoding="utf-8") as f:
        f.write(f"{(datetime.datetime.now() - start_time).seconds / 60:.2f} minutes\n")
    
    # Record final results
    # recorder.record_end(result, start_time)
###### Pika onboard ######